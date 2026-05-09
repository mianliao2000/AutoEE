# Model Backend Progress

## Final Goal
- Provide a secure, swappable LLM backend for AutoEE GUI workflow steps.
- Keep deterministic engineering calculations outside the LLM boundary.
- Support OpenAI, Anthropic, Gemini, OpenRouter, Ollama, custom OpenAI-compatible endpoints, and a mock fallback.

## Completed
- Added provider interface with `chat`, `structured_json`, `stream`, `tool_call`, and `health_check`.
- Added explicit provider adapters and a mock provider for offline testing.
- Added keyring-backed secret store with in-memory fallback for tests.
- Added secret redaction/fingerprint helpers so config, logs, and reports never store full keys.
- Added reserved ChatGPT OAuth placeholder explaining that desktop API calls use API keys.

## Verification
- Unit tests cover provider config validation, redaction, mock JSON responses, provider switching, and config serialization without secrets.

## Risks And Blockers
- ChatGPT OAuth is intentionally not implemented for desktop API billing; future ChatGPT Apps/Actions integration needs a separate backend flow.
- Live provider tests require user-owned API keys and should not run in CI by default.

## Next Steps
- Wire model calls into `spec_analyzer`, `component_search`, `kicad_freecad`, and `report_generator` modules as those modules are created.
- Add provider-specific structured output support where APIs support native schema enforcement.

