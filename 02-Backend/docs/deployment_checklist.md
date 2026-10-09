# Deployment Checklist

## Pre-flight
- [ ] `DATABASE_URL`, `REDIS_URL`, `NEO4J_URI`, `JAEGER_URL` set.
- [ ] `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_GENERATIVEAI_API_KEY` set.
- [ ] `JWT_SECRET_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` set.
- [ ] `ALLOWED_ORIGINS` configured (no wildcard with credentials).
- [ ] `requirements.txt` / `pyproject.toml` deps up to date.

## Container Build
- [ ] `docker-compose build` succeeds.
- [ ] Image runs as non-root `appuser` (Dockerfile).
- [ ] Health checks pass: `/health`, `/health/liveness`, `/health/readiness`.
- [ ] `/metrics` endpoint returns Prometheus data.

## Services
- [ ] Postgres (pgvector) healthy and migrations applied (`alembic/`).
- [ ] Redis reachable and memory policy set.
- [ ] Neo4j reachable with APOC plugin.
- [ ] Jaeger tracing ingesting.
- [ ] Prometheus + Grafana scraping.

## Runtime
- [ ] Replicas scaled in `docker-compose.yml` or k8s (`k8s/`).
- [ ] Resource limits / reservations set.
- [ ] Logs aggregated (structlog).
- [ ] Backups scheduled (`scripts/daily_backup.py`, `scripts/restore_db.py`).
