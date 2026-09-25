# ADR-0004: Multi-Model Routing

- **Status**: Accepted
- **Date**: 2026-09-17
- **Context**: AstrovoxAi supports multiple LLM providers (OpenAI, Anthropic, local models). Requests must be routed to the appropriate model based on capabilities, cost, and availability.

## Decision
Implement a **Strategy-based Model Router** in the core orchestration layer.

## Rationale
- Decouples API surface from model-specific implementations.
- Enables runtime switching via config without service restarts.
- Supports fallback chains for resilience during provider outages.
- Testable via injected router strategies.

## Consequences
- All chat completions must pass through the router abstraction.
- Provider adapters must implement a common `ModelProvider` interface.
- Routing decisions must be logged for observability and cost analysis.
