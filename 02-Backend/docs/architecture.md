# Architecture

AstrovoxAi Engine is an async FastAPI backend (Python 3.11) built for production AI chat, reasoning, and multi-agent workloads.

## High-Level Components

| Layer | Path / Tool | Responsibility |
|------|------------|----------------|
| API Gateway | `app/main.py`, `app/routers/*` | HTTP entry, auth, routing |
| Services | `app/services/*` | Business logic, provider orchestration |
| Intelligence | `intelligence_router.py`, `model_router_v2.py` | LLM routing, budget caps, fallbacks |
| Persistence | Postgres (pgvector), Redis, Neo4j | Relational, cache, graph |
| Observability | Prometheus, Jaeger, Grafana | Metrics, traces, dashboards |
| Infrastructure | Docker, docker-compose, `k8s/` | Container orchestration |

## Request Flow

1. HTTP enters `app/main.py` through CORS → security headers → rate limit → metrics middleware.
2. Routers resolve endpoints (auth, chat, memory, terminal, embeddings, models, safety).
3. Services call Supabase Postgres, Redis cache, and Neo4j graph as needed.
4. LLM calls route through the intelligence layer with budget caps and fallback policies.

## Data Stores

- **Postgres (pgvector)**: Primary relational store; stores conversations, users, embeddings via pgvector for similarity search.
- **Redis**: Session store, rate limiter, semantic cache, pub/sub for real-time events.
- **Neo4j**: Knowledge graph for relationships, memory chains, and reasoning paths.

## Extensibility

- New routers are added in `app/routers/` and included in `app/main.py`.
- New services follow the `app/services/*` pattern and are injected via dependency injection.
- LLM providers are registered in the intelligence router; see `intelligence_router.py` for the provider interface.

## Scaling Model

- The app is stateless; scale horizontally behind the same Postgres/Redis/Neo4j stack.
- Use connection pooling (e.g., `pg8000`/`asyncpg`) and Redis clustering for high throughput.
- See `docker-compose.yml` for local multi-replica deployment.
