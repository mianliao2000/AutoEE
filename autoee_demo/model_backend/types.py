from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


Message = Mapping[str, str]


@dataclass
class ProviderConfig:
    provider: str
    model: str
    base_url: str = ""
    api_key_env: str = ""
    secret_name: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "secret_name": self.secret_name,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ProviderConfig":
        return cls(
            provider=str(raw.get("provider", "mock")),
            model=str(raw.get("model", "mock-engineer")),
            base_url=str(raw.get("base_url", "")),
            api_key_env=str(raw.get("api_key_env", "")),
            secret_name=str(raw.get("secret_name", "")),
            extra=dict(raw.get("extra", {})),
        )


@dataclass
class ModelResponse:
    text: str
    provider: str
    model: str
    raw: Dict[str, Any] = field(default_factory=dict)
    usage: Dict[str, Any] = field(default_factory=dict)
    unavailable: bool = False


@dataclass
class HealthCheck:
    ok: bool
    provider: str
    message: str
    fingerprint: str = "none"


def normalize_messages(messages: Iterable[Mapping[str, str]]) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = str(message.get("content", ""))
        result.append({"role": role, "content": content})
    return result


def validate_provider_config(config: ProviderConfig) -> List[str]:
    errors: List[str] = []
    if not config.provider:
        errors.append("Provider is required.")
    if not config.model:
        errors.append("Model id is required.")
    if config.provider in {"openai", "anthropic", "gemini", "openrouter", "custom_openai"}:
        if not config.secret_name and not config.api_key_env:
            errors.append("Cloud providers need a keyring secret name or environment variable.")
    if config.provider in {"openai", "openrouter", "ollama", "custom_openai"} and not config.base_url:
        errors.append("Provider base URL is required.")
    return errors


def extract_text_from_openai_responses(raw: Mapping[str, Any]) -> str:
    if isinstance(raw.get("output_text"), str):
        return str(raw["output_text"])
    chunks: List[str] = []
    for item in raw.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and "text" in content:
                chunks.append(str(content["text"]))
    return "\n".join(chunks).strip()


def extract_text_from_chat_completions(raw: Mapping[str, Any]) -> str:
    choices = raw.get("choices", []) or []
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return str(message.get("content", "")).strip()


OptionalJsonSchema = Optional[Mapping[str, Any]]

