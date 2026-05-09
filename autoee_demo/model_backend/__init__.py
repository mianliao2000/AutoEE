"""Pluggable LLM backend layer for AutoEE."""

from .auth import ChatGPTOAuthPlaceholder
from .manager import ModelManager
from .providers import (
    AnthropicProvider,
    CustomOpenAICompatibleProvider,
    GeminiProvider,
    MockProvider,
    ModelProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
)
from .registry import ProviderRegistry
from .secrets import KeyringSecretStore, MemorySecretStore, redact_secret, secret_fingerprint
from .settings import ModelBackendSettings
from .types import HealthCheck, ModelResponse, ProviderConfig

__all__ = [
    "AnthropicProvider",
    "ChatGPTOAuthPlaceholder",
    "CustomOpenAICompatibleProvider",
    "GeminiProvider",
    "HealthCheck",
    "KeyringSecretStore",
    "MemorySecretStore",
    "MockProvider",
    "ModelBackendSettings",
    "ModelManager",
    "ModelProvider",
    "ModelResponse",
    "OllamaProvider",
    "OpenAIProvider",
    "OpenRouterProvider",
    "ProviderConfig",
    "ProviderRegistry",
    "redact_secret",
    "secret_fingerprint",
]

