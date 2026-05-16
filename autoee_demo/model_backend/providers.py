from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional

import requests

from .secrets import SecretStore, redact_secret, resolve_secret, secret_fingerprint
from .types import (
    HealthCheck,
    Message,
    ModelResponse,
    OptionalJsonSchema,
    ProviderConfig,
    extract_text_from_chat_completions,
    extract_text_from_openai_responses,
    normalize_messages,
)


class ModelProvider(ABC):
    def __init__(self, config: ProviderConfig, secret_store: SecretStore):
        self.config = config
        self.secret_store = secret_store

    @property
    def name(self) -> str:
        return self.config.provider

    def _api_key(self) -> str:
        return resolve_secret(self.secret_store, self.config.secret_name, self.config.api_key_env)

    @abstractmethod
    def chat(
        self,
        messages: Iterable[Message],
        context: Optional[Mapping[str, Any]] = None,
        tools: Optional[Iterable[Mapping[str, Any]]] = None,
        timeout: float = 30.0,
    ) -> ModelResponse:
        raise NotImplementedError

    def structured_json(
        self,
        messages: Iterable[Message],
        schema: OptionalJsonSchema = None,
        context: Optional[Mapping[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        schema_note = f"\nReturn JSON matching this schema: {json.dumps(schema, sort_keys=True)}" if schema else ""
        augmented = list(normalize_messages(messages))
        augmented.append({"role": "user", "content": "Return only valid JSON." + schema_note})
        response = self.chat(augmented, context=context, timeout=timeout)
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"raw_text": response.text, "provider": response.provider, "unavailable": response.unavailable}

    def stream(
        self,
        messages: Iterable[Message],
        context: Optional[Mapping[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Iterator[str]:
        yield self.chat(messages, context=context, timeout=timeout).text

    def tool_call(
        self,
        messages: Iterable[Message],
        tools: Iterable[Mapping[str, Any]],
        context: Optional[Mapping[str, Any]] = None,
        timeout: float = 30.0,
    ) -> ModelResponse:
        return self.chat(messages, context=context, tools=tools, timeout=timeout)

    def health_check(self, timeout: float = 10.0) -> HealthCheck:
        key = self._api_key()
        return HealthCheck(
            ok=bool(key),
            provider=self.name,
            message="API key is configured." if key else "API key is not configured.",
            fingerprint=secret_fingerprint(key),
        )


class MockProvider(ModelProvider):
    def chat(
        self,
        messages: Iterable[Message],
        context: Optional[Mapping[str, Any]] = None,
        tools: Optional[Iterable[Mapping[str, Any]]] = None,
        timeout: float = 30.0,
    ) -> ModelResponse:
        normalized = normalize_messages(messages)
        last_user = next((m["content"] for m in reversed(normalized) if m["role"] == "user"), "")
        text = (
            "Mock AI backend active. Deterministic modules own numeric specs, losses, "
            f"thermal results, and simulations. Last request: {last_user[:160]}"
        )
        return ModelResponse(text=text, provider=self.name, model=self.config.model, raw={"mock": True})

    def structured_json(
        self,
        messages: Iterable[Message],
        schema: OptionalJsonSchema = None,
        context: Optional[Mapping[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.config.model,
            "mock": True,
            "schema_keys": sorted((schema or {}).keys()),
            "context_keys": sorted((context or {}).keys()),
        }

    def health_check(self, timeout: float = 10.0) -> HealthCheck:
        return HealthCheck(ok=True, provider=self.name, message="Mock provider is always available.")


class OpenAIProvider(ModelProvider):
    def chat(
        self,
        messages: Iterable[Message],
        context: Optional[Mapping[str, Any]] = None,
        tools: Optional[Iterable[Mapping[str, Any]]] = None,
        timeout: float = 30.0,
    ) -> ModelResponse:
        api_key = self._api_key()
        if not api_key:
            return ModelResponse(
                text="AI unavailable: OpenAI API key is not configured.",
                provider=self.name,
                model=self.config.model,
                unavailable=True,
            )
        normalized = normalize_messages(messages)
        prompt_context = f"\n\nAutoEE context:\n{json.dumps(context, sort_keys=True)}" if context else ""
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "input": normalized + ([{"role": "user", "content": prompt_context}] if prompt_context else []),
        }
        if tools:
            payload["tools"] = list(tools)
        response = requests.post(
            f"{self.config.base_url.rstrip('/')}/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        raw = response.json()
        return ModelResponse(
            text=extract_text_from_openai_responses(raw),
            provider=self.name,
            model=self.config.model,
            raw=raw,
            usage=dict(raw.get("usage", {}) or {}),
        )

    def health_check(self, timeout: float = 10.0) -> HealthCheck:
        api_key = self._api_key()
        if not api_key:
            return HealthCheck(False, self.name, "OpenAI API key is not configured.", "none")
        try:
            response = requests.get(
                f"{self.config.base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception as exc:
            return HealthCheck(False, self.name, f"OpenAI health check failed: {exc}", secret_fingerprint(api_key))
        return HealthCheck(True, self.name, "OpenAI health check succeeded.", secret_fingerprint(api_key))


class OpenAICompatibleProvider(ModelProvider):
    def chat(
        self,
        messages: Iterable[Message],
        context: Optional[Mapping[str, Any]] = None,
        tools: Optional[Iterable[Mapping[str, Any]]] = None,
        timeout: float = 30.0,
    ) -> ModelResponse:
        api_key = self._api_key()
        if not api_key:
            return ModelResponse(
                text=f"AI unavailable: {self.name} API key is not configured.",
                provider=self.name,
                model=self.config.model,
                unavailable=True,
            )
        normalized = normalize_messages(messages)
        if context:
            normalized.append({"role": "user", "content": f"AutoEE context:\n{json.dumps(context, sort_keys=True)}"})
        payload: Dict[str, Any] = {"model": self.config.model, "messages": normalized}
        if tools:
            payload["tools"] = list(tools)
        response = requests.post(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        raw = response.json()
        return ModelResponse(
            text=extract_text_from_chat_completions(raw),
            provider=self.name,
            model=self.config.model,
            raw=raw,
            usage=dict(raw.get("usage", {}) or {}),
        )


class OpenRouterProvider(OpenAICompatibleProvider):
    pass


class MiniMaxProvider(OpenAICompatibleProvider):
    pass


class DeepSeekProvider(OpenAICompatibleProvider):
    pass


class QwenProvider(OpenAICompatibleProvider):
    pass


class CustomOpenAICompatibleProvider(OpenAICompatibleProvider):
    pass


class OllamaProvider(ModelProvider):
    def _api_key(self) -> str:
        return ""

    def chat(
        self,
        messages: Iterable[Message],
        context: Optional[Mapping[str, Any]] = None,
        tools: Optional[Iterable[Mapping[str, Any]]] = None,
        timeout: float = 30.0,
    ) -> ModelResponse:
        normalized = normalize_messages(messages)
        if context:
            normalized.append({"role": "user", "content": f"AutoEE context:\n{json.dumps(context, sort_keys=True)}"})
        response = requests.post(
            f"{self.config.base_url.rstrip('/')}/api/chat",
            json={"model": self.config.model, "messages": normalized, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
        raw = response.json()
        text = str((raw.get("message") or {}).get("content", ""))
        return ModelResponse(text=text, provider=self.name, model=self.config.model, raw=raw)

    def health_check(self, timeout: float = 10.0) -> HealthCheck:
        try:
            response = requests.get(f"{self.config.base_url.rstrip('/')}/api/tags", timeout=timeout)
            response.raise_for_status()
        except Exception as exc:
            return HealthCheck(False, self.name, f"Ollama health check failed: {exc}", "none")
        return HealthCheck(True, self.name, "Ollama health check succeeded.", "none")


class AnthropicProvider(ModelProvider):
    def chat(
        self,
        messages: Iterable[Message],
        context: Optional[Mapping[str, Any]] = None,
        tools: Optional[Iterable[Mapping[str, Any]]] = None,
        timeout: float = 30.0,
    ) -> ModelResponse:
        api_key = self._api_key()
        if not api_key:
            return ModelResponse("AI unavailable: Anthropic API key is not configured.", self.name, self.config.model, unavailable=True)
        normalized = normalize_messages(messages)
        system = "\n".join(m["content"] for m in normalized if m["role"] == "system")
        user_messages = [m for m in normalized if m["role"] != "system"]
        if context:
            user_messages.append({"role": "user", "content": f"AutoEE context:\n{json.dumps(context, sort_keys=True)}"})
        payload = {"model": self.config.model, "max_tokens": 2048, "system": system, "messages": user_messages}
        response = requests.post(
            f"{self.config.base_url.rstrip('/')}/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        raw = response.json()
        text = "\n".join(str(item.get("text", "")) for item in raw.get("content", []) if item.get("type") == "text")
        return ModelResponse(text=text, provider=self.name, model=self.config.model, raw=raw, usage=dict(raw.get("usage", {}) or {}))


class GeminiProvider(ModelProvider):
    def chat(
        self,
        messages: Iterable[Message],
        context: Optional[Mapping[str, Any]] = None,
        tools: Optional[Iterable[Mapping[str, Any]]] = None,
        timeout: float = 30.0,
    ) -> ModelResponse:
        api_key = self._api_key()
        if not api_key:
            return ModelResponse("AI unavailable: Gemini API key is not configured.", self.name, self.config.model, unavailable=True)
        text = "\n".join(f"{m['role']}: {m['content']}" for m in normalize_messages(messages))
        if context:
            text += f"\nAutoEE context:\n{json.dumps(context, sort_keys=True)}"
        response = requests.post(
            f"{self.config.base_url.rstrip('/')}/models/{self.config.model}:generateContent",
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": text}]}]},
            timeout=timeout,
        )
        response.raise_for_status()
        raw = response.json()
        parts = []
        for candidate in raw.get("candidates", []) or []:
            for part in (candidate.get("content") or {}).get("parts", []) or []:
                if "text" in part:
                    parts.append(str(part["text"]))
        return ModelResponse(text="\n".join(parts), provider=self.name, model=self.config.model, raw=raw)


def provider_secret_summary(provider: ModelProvider) -> str:
    key = provider._api_key()
    return redact_secret(key) if key else "not configured"
