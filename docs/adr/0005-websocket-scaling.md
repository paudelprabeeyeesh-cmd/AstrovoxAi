# ADR-0005: WebSocket Scaling

- **Status**: Accepted
- **Date**: 2026-09-17
- **Context**: AstrovoxAi uses WebSockets for real-time streaming responses. Horizontal scaling requires a shared pub/sub mechanism to broadcast messages across multiple workers.

## Decision
Use **Redis Pub/Sub** as the WebSocket backplane for horizontal scaling.

## Rationale
- No additional infrastructure required (Redis is already selected for caching).
- Simple fan-out semantics match WebSocket broadcast requirements.
- Supports worker affinity through consistent hashing on channel names.

## Consequences
- Each WebSocket connection subscribes to a Redis channel keyed by session ID.
- Connection lifecycle events must publish to Redis for cross-worker awareness.
- Large broadcast payloads should consider compression or chunking.
