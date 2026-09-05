# Release Notes — v1.0.0

## Summary

AstravoxAi Engine v1.0.0 is the initial stable release of the production-grade asynchronous stateless backend for AI chat.

## What's New

- Multi-provider AI chat with OpenAI, Anthropic, Google Gemini, and Ollama
- Streaming responses via Server-Sent Events
- AI memory system with persistent context
- Embeddings API with batch support
- Conversation history management
- Interactive terminal console
- Rate limiting and security hardening
- Prometheus metrics and structured logging
- Docker Compose deployment
- CI/CD pipeline with GitHub Actions

## Bug Fixes

- Fixed event bus import conflict between `app/events.py` and `app/events/` package
- Fixed compiler optimization pipeline: fusion, dead-step elimination, cost estimation, parallel groups
- Fixed plan cache isolation to prevent test mutations from leaking
- Fixed runtime `_echo_handler` to use correct `CompiledStep` attributes
- Fixed workflow engine template creation and cloning

## Infrastructure

- Added `CONTRIBUTING.md`, `SECURITY.md`, and `DEVELOPER_GUIDE.md`
- Resolved 141 backend tests across compiler, runtime, kernel, integration, security, performance, infrastructure, and workflow suites
- Cleaned up unused imports and dead code

## Known Limitations

- Some integration and E2E tests expose pre-existing rate-limiting test isolation issues
- Frontend build and typecheck commands should be run separately

## Upgrade Path

This is the first stable release. No migration needed.

## Links

- Documentation: See `README.md`, `API.md`, `DEPLOYMENT.md`, `DEVELOPER_GUIDE.md`
- Issues: https://github.com/<your-username>/AstrovoxAi/issues
