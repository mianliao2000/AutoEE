from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping

from .registry import DEFAULT_PROVIDER_CONFIGS
from .types import ProviderConfig


def default_settings_path() -> Path:
    return Path.home() / ".autoee" / "model_backend.json"


@dataclass
class ModelBackendSettings:
    default_provider: str = "openai"
    configs: Dict[str, ProviderConfig] = field(
        default_factory=lambda: {
            name: ProviderConfig.from_dict(config.to_public_dict())
            for name, config in DEFAULT_PROVIDER_CONFIGS.items()
        }
    )
    per_step_overrides: Dict[str, str] = field(default_factory=dict)
    chatgpt_oauth_reserved: bool = True

    def provider_config(self, provider_name: str = "") -> ProviderConfig:
        name = provider_name or self.default_provider
        if name not in self.configs:
            raise ValueError(f"Provider is not configured: {name}")
        return self.configs[name]

    def set_provider_config(self, config: ProviderConfig) -> None:
        self.configs[config.provider] = config

    def provider_for_step(self, step_name: str) -> str:
        return self.per_step_overrides.get(step_name, self.default_provider)

    def to_dict(self) -> Dict[str, object]:
        return {
            "default_provider": self.default_provider,
            "configs": {name: config.to_public_dict() for name, config in self.configs.items()},
            "per_step_overrides": dict(self.per_step_overrides),
            "chatgpt_oauth_reserved": self.chatgpt_oauth_reserved,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "ModelBackendSettings":
        settings = cls()
        settings.default_provider = str(raw.get("default_provider", settings.default_provider))
        configs = raw.get("configs", {})
        if isinstance(configs, Mapping):
            for name, value in configs.items():
                if isinstance(value, Mapping):
                    settings.configs[str(name)] = ProviderConfig.from_dict(value)
        overrides = raw.get("per_step_overrides", {})
        if isinstance(overrides, Mapping):
            settings.per_step_overrides = {str(k): str(v) for k, v in overrides.items()}
        settings.chatgpt_oauth_reserved = bool(raw.get("chatgpt_oauth_reserved", True))
        return settings

    def save(self, path: Path | None = None) -> Path:
        target = path or default_settings_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: Path | None = None) -> "ModelBackendSettings":
        target = path or default_settings_path()
        if not target.exists():
            return cls()
        return cls.from_dict(json.loads(target.read_text(encoding="utf-8")))

