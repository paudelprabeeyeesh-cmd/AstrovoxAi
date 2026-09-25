# ADR-0001: Use FastAPI for API Layer

- **Status**: Accepted
- **Date**: 2026-09-17
- **Context**: AstrovoxAi requires a high-performance API layer with async support, OpenAPI generation, and WebSocket support for streaming AI responses.

## Decision
Adopt **FastAPI** as the primary web framework for the API layer.

## Rationale
- Native async/await support for high concurrency.
- Built-in OpenAPI 3.1 schema generation.
- Pydantic validation aligns with existing data contracts.
- WebSocket support via `fastapi.WebSocket`.
- Broad ecosystem compatibility with async Python libraries.

## Consequences
- All API handlers must be async or properly wrapped.
- Synchronous dependencies must run in thread pools via `asyncio.to_thread`.
- Testing must use `httpx.AsyncClient` or `pytest-asyncio`.
