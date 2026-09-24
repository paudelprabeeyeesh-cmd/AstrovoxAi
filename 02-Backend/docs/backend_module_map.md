# Backend Module Map

## Entrypoint
- `app/main.py` — FastAPI app assembly, middleware, routers, health endpoints.

## Configuration
- `app/config.py` — Env settings: API keys, DB URLs, JWT, Stripe, model aliases, budget caps.

## Routing
- `app/routers/` — Modular routers for models, memory controls, safety API.
- `app/auth.py`, `app/chat.py`, `app/audit.py`, `app/secrets.py`, `app/storage.py`, `app/telemetry.py`, `app/terminal.py`, `app/embeddings_route.py` — Top-level routers.

## Data Access
- `app/database.py` — Supabase CRUD for profiles, conversations, messages, memory, settings.
- `database/database.py` — Secondary DB helper.
- `app/supabase_client.py` — Supabase client factory.

## Intelligence Layer
- `app/model_router_v2.py`, `app/intelligence_router.py` — Model routing, budget enforcement.
- `app/rag_engine.py`, `app/graph_rag.py`, `app/graph_rag_v2.py` — Retrieval.
- `app/knowledge_graph.py`, `app/knowledge_graph_neo4j.py` — Knowledge graph.
- `app/memory_*.py` — Memory routing, pipeline, intelligence.

## Observability & Safety
- `app/metrics.py` — Prometheus.
- `app/logging_config.py`, `app/observability.py` — Structured logging.
- `app/security.py`, `app/rate_limit.py`, `app/circuit_breaker.py`, `app/fallback.py` — Resilience.
