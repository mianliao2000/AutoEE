from __future__ import annotations

from typing import Dict, Type

from .providers import (
    AnthropicProvider,
    CustomOpenAICompatibleProvider,
    DeepSeekProvider,
    GeminiProvider,
    MiniMaxProvider,
    MockProvider,
    ModelProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
    QwenProvider,
)
from .secrets import SecretStore
from .types import ProviderConfig


DEFAULT_PROVIDER_CONFIGS: Dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        provider="openai",
        model="gpt-5.5",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        secret_name="openai_api_key",
    ),
    "anthropic": ProviderConfig(
        provider="anthropic",
        model="claude-sonnet-4-5",
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        secret_name="anthropic_api_key",
    ),
    "gemini": ProviderConfig(
        provider="gemini",
        model="gemini-2.5-pro",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key_env="GEMINI_API_KEY",
        secret_name="gemini_api_key",
    ),
    "openrouter": ProviderConfig(
        provider="openrouter",
        model="openai/gpt-5.5",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        secret_name="openrouter_api_key",
    ),
    "minimax": ProviderConfig(
        provider="minimax",
        model="MiniMax-M2.7",
        base_url="https://api.minimax.io/v1",
        api_key_env="MINIMAX_API_KEY",
        secret_name="minimax_api_key",
    ),
    "deepseek": ProviderConfig(
        provider="deepseek",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        secret_name="deepseek_api_key",
    ),
    "qwen": ProviderConfig(
        provider="qwen",
        model="qwen-max",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="QWEN_API_KEY",
        secret_name="qwen_api_key",
    ),
    "ollama": ProviderConfig(
        provider="ollama",
        model="llama3.1",
        base_url="http://localhost:11434",
    ),
    "custom_openai": ProviderConfig(
        provider="custom_openai",
        model="custom-model",
        base_url="http://localhost:8000/v1",
        api_key_env="CUSTOM_OPENAI_API_KEY",
        secret_name="custom_openai_api_key",
    ),
    "mock": ProviderConfig(provider="mock", model="mock-engineer"),
}


class ProviderRegistry:
    provider_classes: Dict[str, Type[ModelProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "openrouter": OpenRouterProvider,
        "minimax": MiniMaxProvider,
        "deepseek": DeepSeekProvider,
        "qwen": QwenProvider,
        "ollama": OllamaProvider,
        "custom_openai": CustomOpenAICompatibleProvider,
        "mock": MockProvider,
    }

    def __init__(self, secret_store: SecretStore):
        self.secret_store = secret_store

    def default_config(self, provider_name: str) -> ProviderConfig:
        if provider_name not in DEFAULT_PROVIDER_CONFIGS:
            raise ValueError(f"Unknown provider: {provider_name}")
        raw = DEFAULT_PROVIDER_CONFIGS[provider_name].to_public_dict()
        return ProviderConfig.from_dict(raw)

    def create(self, config: ProviderConfig) -> ModelProvider:
        provider_class = self.provider_classes.get(config.provider)
        if provider_class is None:
            raise ValueError(f"Unknown provider: {config.provider}")
        return provider_class(config, self.secret_store)

    def names(self):
        return list(self.provider_classes.keys())
