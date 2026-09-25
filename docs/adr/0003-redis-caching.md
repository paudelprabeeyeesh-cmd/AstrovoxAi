# ADR-0003: Use Redis for Caching

- **Status**: Accepted
- **Date**: 2026-09-17
- **Context**: AstrovoxAi needs low-latency caching for session state, rate limiting counters, and hot model routing decisions.

## Decision
Adopt **Redis** as the caching layer for hot-path data.

## Rationale
- Sub-millisecond latency for GET/SET operations.
- Native support for TTL-based expiration.
- Pub/sub available for future event streaming needs.
- Widely deployed and operationally mature.

## Consequences
- Cache keys must follow a namespaced convention (`astrovox:{domain}:{id}`).
- Cache invalidation must be explicit on data mutations.
- Redis failures must degrade gracefully to database reads.
