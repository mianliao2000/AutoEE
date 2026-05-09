from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from .registry import ProviderRegistry
from .secrets import KeyringSecretStore, MemorySecretStore, SecretStore
from .settings import ModelBackendSettings
from .types import HealthCheck, Message, ModelResponse, OptionalJsonSchema


class ModelManager:
    """Convenience facade used by workflow modules and the GUI."""

    def __init__(
        self,
        settings: Optional[ModelBackendSettings] = None,
        secret_store: Optional[SecretStore] = None,
    ):
        self.settings = settings or ModelBackendSettings()
        if secret_store is not None:
            self.secret_store = secret_store
        elif KeyringSecretStore.available():
            self.secret_store = KeyringSecretStore()
        else:
            self.secret_store = MemorySecretStore()
        self.registry = ProviderRegistry(self.secret_store)

    def provider(self, provider_name: str = ""):
        return self.registry.create(self.settings.provider_config(provider_name))

    def provider_for_step(self, step_name: str):
        return self.provider(self.settings.provider_for_step(step_name))

    def chat(
        self,
        messages: Iterable[Message],
        context: Optional[Mapping[str, Any]] = None,
        provider_name: str = "",
        timeout: float = 30.0,
    ) -> ModelResponse:
        return self.provider(provider_name).chat(messages, context=context, timeout=timeout)

    def structured_json(
        self,
        messages: Iterable[Message],
        schema: OptionalJsonSchema = None,
        context: Optional[Mapping[str, Any]] = None,
        provider_name: str = "",
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        return self.provider(provider_name).structured_json(messages, schema=schema, context=context, timeout=timeout)

    def health_check(self, provider_name: str = "", timeout: float = 10.0) -> HealthCheck:
        return self.provider(provider_name).health_check(timeout=timeout)

    def save_settings(self, path: Optional[Path] = None) -> Path:
        return self.settings.save(path)

