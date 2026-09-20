# AstrovoxAI - Deployment Guide

## Rollback Strategy

### Docker Compose
```bash
docker compose pull
docker compose up -d --force-recreate
cd 02-Backend && alembic downgrade -1
```

### Kubernetes
```bash
kubectl rollout undo deployment/astrovox-api -n astrovox
kubectl rollout undo deployment/astrovox-worker -n astrovox
```

### Render
1. Go to Dashboard > Deployments
2. Click Previous deployment
3. Click Promote

## Pre-Deployment Checklist
- [ ] All tests pass: cd 02-Backend && python -m pytest tests/
- [ ] No hardcoded secrets
- [ ] .env.example is up to date
- [ ] Docker image builds: docker build -t astrovox-api .
- [ ] Health check passes: /health returns 200

## Environment Variables
See .env.example for complete list. Minimum required:
- DATABASE_URL
- REDIS_URL
- OPENAI_API_KEY
- JWT_SECRET_KEY
- ALLOWED_ORIGINS

## Health Checks
- /health - Overall health status
- /health/detailed - Detailed component health (requires auth)
- /ready - Readiness probe (Kubernetes)
- /live - Liveness probe (Kubernetes)
- /healthz - Legacy health endpoint

## Monitoring
- Prometheus metrics: /metrics/prometheus (unauthenticated)
- Application metrics: /metrics (requires admin)
- Grafana dashboard: http://localhost:3000 (docker-compose)
- Jaeger traces: http://localhost:16686

## Backup and Restore
```bash
./scripts/backup-db.sh
./scripts/backup-redis.sh
./scripts/restore-db.sh ./backups/postgres/astrovox_YYYYMMDD_HHMMSS.sql.gz
./scripts/restore-redis.sh ./backups/redis/redis_YYYYMMDD_HHMMSS.rdb.gz
```
