# Architecture Overview

AstrovoxAi Engine is an async FastAPI backend (Python 3.12) built for production AI chat, reasoning, and multi-agent workloads.

## Core Stack

- **Framework**: FastAPI + Uvicorn (async)
- **Datastores**: Postgres (pgvector), Redis, Neo4j
- **LLM Providers**: OpenAI, Anthropic, Google Generative AI
- **Observability**: Prometheus, Jaeger, Grafana
- **Config**: `python-dotenv` via `app/config.py`

## High-Level Components

| Layer | Path / Tool | Responsibility |
|------|------------|----------------|
| API Gateway | `app/main.py`, `app/routers/*` | HTTP entry, auth, routing |
| Services | `app/services/*` | Business logic, provider orchestration |
| Intelligence | `intelligence_router.py`, `model_router_v2.py` | LLM routing, budget caps, fallbacks |
| Persistence | Postgres (pgvector), Redis, Neo4j | Relational, cache, graph |
| Observability | Prometheus, Jaeger, Grafana | Metrics, traces, dashboards |
| Infrastructure | Docker, docker-compose, `k8s/`, Helm | Container orchestration |

## Request Flow

1. HTTP enters `app/main.py` through CORS → security headers → rate limit → metrics middleware.
2. Routers resolve endpoints (auth, chat, memory, terminal, embeddings, models, safety).
3. Services call Supabase Postgres, Redis cache, and Neo4j graph as needed.
4. LLM calls route through the intelligence layer with budget caps and fallback policies.

## Data Stores

- **Postgres (pgvector)**: Primary relational store; stores conversations, users, embeddings via pgvector for similarity search.
- **Redis**: Session store, rate limiter, semantic cache, pub/sub for real-time events.
- **Neo4j**: Knowledge graph for relationships, memory chains, and reasoning paths.

## Security Architecture

- **Transport**: TLS 1.3 enforced via ingress/nginx; HSTS headers
- **Authentication**: JWT with short-lived tokens; Supabase auth integration
- **Authorization**: Role-based access control (admin, user roles)
- **Secrets**: Managed via Kubernetes secrets / environment variables; never in code
- **Network**: Private network; pod-to-pod communication restricted by NetworkPolicy
- **Container Security**: Non-root user, read-only root filesystem, dropped capabilities, seccomp profile

## Observability

- **Metrics**: Prometheus client (`prometheus-client`); scraped at `/metrics`
- **Traces**: OpenTelemetry → Jaeger for distributed tracing
- **Logs**: Structured JSON logging via `structlog`; aggregated by Promtail → Loki
- **Dashboards**: Grafana dashboards for request rate, latency, errors, DB health

## Extensibility

- New routers are added in `app/routers/` and included in `app/main.py`.
- New services follow the `app/services/*` pattern and are injected via dependency injection.
- LLM providers are registered in the intelligence router; see `intelligence_router.py` for the provider interface.

## Scaling Model

- The app is stateless; scale horizontally behind the same Postgres/Redis/Neo4j stack.
- Use connection pooling (e.g., `asyncpg`) and Redis clustering for high throughput.
- Kubernetes HPA scales based on CPU (70%) and memory (80%).
- See `k8s/` for production manifests and `helm/` for packaged deployment.

## CI/CD Pipeline

1. **CI**: Lint (ruff, eslint), typecheck, tests (pytest, vitest)
2. **Security**: Gitleaks secret scan, Trivy vulnerability scan, dependency review
3. **Docker**: Multi-arch build (amd64, arm64), pushed to GHCR with build cache
4. **Deploy**: Automated staging on develop branch, production on version tags

## Environments

- **Local**: `docker-compose up` spins up the full stack on `localhost:8000`
- **Staging**: Kubernetes on EKS; deployed from `develop` branch
- **Production**: Kubernetes on EKS; deployed from version tags
