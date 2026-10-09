# Deployment Guide

## Environments

- **Local**: `docker-compose up` spins up the full stack on `localhost:8000`.
- **Staging / Production**: Container images are built from `Dockerfile` and deployed behind a reverse proxy or Kubernetes.

## Pre-Flight

- Set required environment variables: `DATABASE_URL`, `REDIS_URL`, `NEO4J_URI`, `JAEGER_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_GENERATIVEAI_API_KEY`, `JWT_SECRET_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.
- Configure `ALLOWED_ORIGINS` with explicit domains; never use wildcard origins with credentials.
- Confirm `requirements.txt` / `pyproject.toml` dependencies are up to date.

## Container Build

```bash
docker-compose build
docker-compose up -d
```

- Image runs as non-root `appuser` (see `Dockerfile`).
- Health checks: `/health`, `/health/liveness`, `/health/readiness`.
- `/metrics` exposes Prometheus data.

## Services

- **Postgres (pgvector)**: Run migrations via `alembic/`; verify `pgvector` extension is installed.
- **Redis**: Set `maxmemory-policy` (e.g., `allkeys-lru`); confirm persistence settings.
- **Neo4j**: Ensure APOC plugin is enabled; check bolt connectivity.
- **Jaeger**: Confirm trace ingestion at `http://jaeger:14268/api/traces`.
- **Prometheus + Grafana**: Scrape `/metrics`; import dashboards for FastAPI, Redis, Postgres.

## Runtime

- Scale app replicas in `docker-compose.yml` or Kubernetes manifests (`k8s/`).
- Set resource limits and reservations per service.
- Aggregate logs with `structlog`; ship to your logging backend.
- Schedule backups: `scripts/daily_backup.py` and `scripts/restore_db.py`.

## Kubernetes

- See `k8s/` for deployment, service, and ingress manifests.
- Use health probes (`livenessProbe`, `readinessProbe`) matching the container health checks.
- Configure `HorizontalPodAutoscaler` based on CPU or custom metrics.

## Rollback

- Revert to the previous image tag in your orchestrator.
- Use database migration rollback (`alembic downgrade`) only if necessary; prefer forward migrations with repair.
