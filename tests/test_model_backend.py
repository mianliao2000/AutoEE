import json
import tempfile
import unittest
from pathlib import Path

from autoee_demo.core import DesignState, run_synthetic_workflow
from autoee_demo.model_backend import (
    MemorySecretStore,
    ModelBackendSettings,
    ModelManager,
    ProviderConfig,
    ProviderRegistry,
    redact_secret,
    secret_fingerprint,
)
from autoee_demo.model_backend.types import extract_text_from_chat_completions, validate_provider_config


class ModelBackendTests(unittest.TestCase):
    def test_provider_config_validation(self):
        valid = ProviderConfig(
            provider="openai",
            model="gpt-5.5",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            secret_name="openai_api_key",
        )
        self.assertEqual(validate_provider_config(valid), [])

        invalid = ProviderConfig(provider="openai", model="", base_url="")
        errors = validate_provider_config(invalid)
        self.assertTrue(any("Model id" in err for err in errors))
        self.assertTrue(any("base URL" in err for err in errors))

    def test_secret_redaction_uses_fingerprint(self):
        secret = "secret-token-for-tests"
        redacted = redact_secret(secret)
        self.assertNotIn(secret, redacted)
        self.assertIn(secret_fingerprint(secret), redacted)

    def test_mock_provider_structured_json(self):
        manager = ModelManager(
            ModelBackendSettings(default_provider="mock"),
            MemorySecretStore(),
        )
        result = manager.structured_json(
            [{"role": "user", "content": "Draft specs"}],
            schema={"type": "object", "properties": {"name": {"type": "string"}}},
            context=DesignState().model_context_payload(),
        )
        self.assertTrue(result["mock"])
        self.assertEqual(result["provider"], "mock")
        self.assertIn("properties", result["schema_keys"])

    def test_provider_switching(self):
        store = MemorySecretStore({"openai_api_key": "secret-openai-token"})
        settings = ModelBackendSettings(default_provider="mock")
        manager = ModelManager(settings, store)
        self.assertEqual(manager.provider().name, "mock")
        settings.default_provider = "openai"
        self.assertEqual(manager.provider().name, "openai")

    def test_settings_serialization_does_not_include_secret_value(self):
        secret = "secret-value-that-must-not-be-saved"
        settings = ModelBackendSettings(default_provider="openai")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model_backend.json"
            settings.save(path)
            text = path.read_text(encoding="utf-8")
        self.assertNotIn(secret, text)
        parsed = json.loads(text)
        self.assertEqual(parsed["default_provider"], "openai")
        self.assertIn("openai", parsed["configs"])

    def test_synthetic_workflow_runs_without_api_key(self):
        manager = ModelManager(ModelBackendSettings(default_provider="mock"), MemorySecretStore())
        state = run_synthetic_workflow(DesignState(), manager)
        self.assertEqual(state.workflow_status, "synthetic_complete")
        self.assertIn("synthetic_workflow", state.deterministic_results)
        self.assertIn("synthetic_workflow", state.ai_notes)

    def test_registry_has_required_providers(self):
        registry = ProviderRegistry(MemorySecretStore())
        for name in ["openai", "anthropic", "gemini", "openrouter", "minimax", "deepseek", "qwen", "ollama", "custom_openai", "mock"]:
            self.assertIn(name, registry.names())

    def test_minimax_default_provider_config(self):
        registry = ProviderRegistry(MemorySecretStore())
        config = registry.default_config("minimax")
        self.assertEqual(config.provider, "minimax")
        self.assertEqual(config.model, "MiniMax-M2.7")
        self.assertEqual(config.base_url, "https://api.minimax.io/v1")
        self.assertEqual(config.api_key_env, "MINIMAX_API_KEY")

    def test_chat_completion_text_strips_reasoning_blocks(self):
        raw = {
            "choices": [
                {
                    "message": {
                        "content": "<think>\ninternal reasoning\n</think>\n\nFinal answer",
                    },
                },
            ],
        }
        self.assertEqual(extract_text_from_chat_completions(raw), "Final answer")


if __name__ == "__main__":
    unittest.main()
