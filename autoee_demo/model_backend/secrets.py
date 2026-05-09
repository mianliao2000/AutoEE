from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional


SERVICE_NAME = "AutoEE.ModelBackend"


def secret_fingerprint(secret: str) -> str:
    if not secret:
        return "none"
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:10]}"


def redact_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]} ({secret_fingerprint(secret)})"


class SecretStore(ABC):
    @abstractmethod
    def get_secret(self, name: str) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def set_secret(self, name: str, value: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_secret(self, name: str) -> None:
        raise NotImplementedError


class KeyringSecretStore(SecretStore):
    """OS keyring backed secret storage.

    The optional keyring dependency is loaded at runtime so unit tests and CI can
    use MemorySecretStore without requiring desktop keychain access.
    """

    def __init__(self, service_name: str = SERVICE_NAME):
        self.service_name = service_name

    @staticmethod
    def available() -> bool:
        try:
            import keyring  # noqa: F401
        except Exception:
            return False
        return True

    def _keyring(self):
        try:
            import keyring
        except Exception as exc:
            raise RuntimeError("The keyring package is not installed or not available.") from exc
        return keyring

    def get_secret(self, name: str) -> Optional[str]:
        return self._keyring().get_password(self.service_name, name)

    def set_secret(self, name: str, value: str) -> None:
        self._keyring().set_password(self.service_name, name, value)

    def delete_secret(self, name: str) -> None:
        try:
            self._keyring().delete_password(self.service_name, name)
        except Exception:
            return


class MemorySecretStore(SecretStore):
    """Test-only secret store."""

    def __init__(self, initial: Optional[Dict[str, str]] = None):
        self._values = dict(initial or {})

    def get_secret(self, name: str) -> Optional[str]:
        return self._values.get(name)

    def set_secret(self, name: str, value: str) -> None:
        self._values[name] = value

    def delete_secret(self, name: str) -> None:
        self._values.pop(name, None)


def resolve_secret(secret_store: SecretStore, secret_name: str, env_var: str = "") -> str:
    if env_var:
        env_value = os.getenv(env_var)
        if env_value:
            return env_value
    if secret_name:
        return secret_store.get_secret(secret_name) or ""
    return ""

