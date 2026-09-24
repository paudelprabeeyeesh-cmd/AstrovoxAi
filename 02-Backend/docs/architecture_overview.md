# Architecture Overview

AstrovoxAi Engine is an async FastAPI backend (Python 3.11) built for production AI chat and reasoning workloads.

## Core Stack
- **Framework**: FastAPI + Uvicorn
- **Datastores**: Postgres (pgvector), Redis, Neo4j
- **LLM Providers**: OpenAI, Anthropic, Google Generative AI
- **Observability**: Prometheus, Jaeger, Grafana
- **Config**: `python-dotenv` via `app/config.py`

## Request Flow
1. HTTP enters `app/main.py`, passes CORS → security headers → rate limit → metrics middleware.
2. Routers (`app/routers/*`, `app/*.py`) resolve endpoints (auth, chat, memory, terminal, embeddings, models, safety).
3. Services talk to Supabase Postgres, Redis cache, and Neo4j graph.
4. LLM calls route through `model_router_v2.py` / `intelligence_router.py` with budget caps (`config.py`).

## Deployment
Containerized in `Dockerfile`; orchestrated by `docker-compose.yml` with health checks and resource limits. App is stateless; scale horizontally behind the same Postgres/Redis/Neo4j stack.
