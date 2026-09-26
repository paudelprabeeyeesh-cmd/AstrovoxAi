# AstrovoxAI — Deployment Guide

## Overview

This guide covers deploying AstrovoxAI to production using Docker Compose or Kubernetes. It includes environment setup, database configuration, health checks, scaling, backup/restore, and rolling deploys.

## Prerequisites

- Docker 24+ and Docker Compose 2.20+
- Supabase project (production database)
- AI provider API keys (OpenAI, Anthropic, Gemini, or Ollama)
- Domain name with TLS certificate (for production)
- Optional: Kubernetes 1.24+ cluster

---

## Environment Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_URL` | Supabase project URL (backend) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `OPENAI_API_KEY` | OpenAI API key |
| `SECRET_KEY` | Application secret for session signing |
| `REDIS_URL` | Redis connection string |
| `DATABASE_URL` | PostgreSQL connection string (if self-hosted) |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GROQ_API_KEY` | — | Groq API key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | CORS origins |
| `ENVIRONMENT` | `production` | `development`, `staging`, `production` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `RATE_LIMIT` | `120/minute` | Per-IP rate limit |
| `DAILY_AI_LIMIT` | `50` | Daily AI quota per user |
| `GUNICORN_WORKERS` | `4` | Backend worker count |
| `SERVER_HOST` | `0.0.0.0` | Bind address |
| `SERVER_PORT` | `8000` | Backend port |

### Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit with production values
nano .env

# For Docker secrets (recommended for production)
echo "your_db_password" | docker secret create db_password -
```

---

## Docker Deployment

### Quick Start (Development)

```bash
# Copy and configure environment
cp .env.example .env
nano .env

# Start all services
docker-compose up --build
```

Services started:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Redis: localhost:6379
- PostgreSQL: localhost:5432

### Production with Docker Compose

```bash
# Build and start in detached mode
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Verify services
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Docker Compose Services

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| `backend` | `Dockerfile.backend` | 8000 | FastAPI application |
| `frontend` | `Dockerfile.frontend` | 80, 443 | Nginx + React SPA |
| `redis` | `redis:7-alpine` | 6379 | Cache, sessions, rate limiting |
| `postgres` | `pgvector/pgvector:pg16` | 5432 | Primary database |

### Production Compose Features

- **Health checks** — All services have health probes
- **Resource limits** — CPU and memory constraints
- **Restart policy** — `unless-stopped` for resilience
- **Logging** — JSON-file driver with rotation
- **Secrets** — Docker secrets for sensitive values
- **Graceful shutdown** — Pre-stop hooks for zero-downtime deploys

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+ cluster
- `kubectl` configured for your cluster
- Helm 3 (optional, for Helm charts)

### Quick Start

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets
kubectl create secret generic astrovox-secrets \
  --from-literal=supabase-url="$SUPABASE_URL" \
  --from-literal=supabase-key="$SUPABASE_SERVICE_ROLE_KEY" \
  --from-literal=openai-key="$OPENAI_API_KEY" \
  --from-literal=secret-key="$SECRET_KEY" \
  --from-literal=db-password="$DB_PASSWORD"

# Apply manifests
kubectl apply -f k8s/

# Verify
kubectl get pods -n astrovox
kubectl get svc -n astrovox
```

### Kubernetes Resources

| Resource | File | Purpose |
|----------|------|---------|
| Namespace | `k8s/namespace.yaml` | `astrovox` namespace |
| ConfigMap | `k8s/configmap.yaml` | Environment configuration |
| Secret | `k8s/secret.yaml` | Sensitive values |
| PostgreSQL | `k8s/postgres.yaml` | StatefulSet + Service |
| Redis | `k8s/redis.yaml` | Deployment + Service |
| Backend | `k8s/deployment.yaml` | Deployment + HPA + Service |
| Frontend | `k8s/reverse-proxy.yaml` | Nginx Deployment + Service |
| Ingress | `k8s/ingress.yaml` | NGINX Ingress Controller |
| Autoscaling | `k8s/hpa.yaml` | Horizontal Pod Autoscaler |
| PDB | `k8s/pdb.yaml` | Pod Disruption Budget |

### Helm Charts

```bash
# Install with Helm
helm install astrovox ./helm \
  --namespace astrovox \
  --create-namespace \
  --values helm/values.yaml
```

Helm values: `helm/values.yaml`

---

## Database Setup

### Supabase (Recommended)

1. Create a new Supabase project
2. Run the schema SQL:
   ```bash
   # In Supabase SQL Editor
   cat database/schemas/supabase_setup.sql
   ```
3. Apply migrations:
   ```bash
   cd 02-Backend
   alembic upgrade head
   ```

### Self-Hosted PostgreSQL

```bash
# Create database
createdb astrovox

# Run migrations
cd 02-Backend
alembic upgrade head
```

---

## Health Checks

All health endpoints are unauthenticated:

| Endpoint | Purpose |
|----------|---------|
| `GET /healthz` | Basic health check |
| `GET /health/liveness` | Kubernetes liveness probe |
| `GET /health/readiness` | Kubernetes readiness probe (checks DB, Redis) |
| `GET /metrics` | Prometheus metrics |

### Docker Health Check

```bash
# Backend
curl -f http://localhost:8000/health/live

# Frontend
curl -f http://localhost/
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 60
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

## Scaling

### Horizontal Scaling

Backend pods scale based on CPU/memory via HPA:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Database Scaling

- Use Supabase for managed scaling
- Connection pooling via PgBouncer
- Read replicas for reporting queries

### Caching Strategy

- Redis for session storage and rate limiting
- Application-level caching for model lists and embeddings
- CDN for static assets (frontend)

---

## Backup and Restore

### Database Backup

```bash
# Supabase
# Use Supabase dashboard or pg_dump with connection string

# Self-hosted PostgreSQL
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Compressed backup
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Database Restore

```bash
# Self-hosted PostgreSQL
psql $DATABASE_URL < backup_20240101.sql

# Compressed restore
gunzip -c backup_20240101.sql.gz | psql $DATABASE_URL
```

### Automated Backups

```yaml
# Kubernetes CronJob example
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:16
              command:
                - /bin/sh
                - -c
                - pg_dump $DATABASE_URL | gzip > /backups/backup_$(date +%Y%m%d).sql.gz
```

---

## Rolling Deploys

### Kubernetes Rolling Update

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1
```

### Docker Swarm Rolling Update

```bash
docker service update --image astrovox/backend:2.0.1 --update-parallelism 1 --update-delay 30s astrovox_backend
```

### Zero-Downtime Checklist

1. New image builds successfully
2. Health checks pass on new pods
3. Readiness probe delays traffic until app is ready
4. `pre_stop` hook sends SIGUSR1 for graceful drain
5. Old pods terminate only after new pods are ready

---

## TLS / HTTPS

### Using Let's Encrypt (cert-manager)

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: astrovox-tls
spec:
  secretName: astrovox-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - astrovox.ai
    - api.astrovox.ai
```

### Nginx Configuration

TLS termination happens at the ingress or Nginx reverse proxy. Configure in `nginx.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name astrovox.ai;

    ssl_certificate /etc/nginx/tls/tls.crt;
    ssl_certificate_key /etc/nginx/tls/tls.key;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
}
```

---

## Monitoring

### Prometheus Configuration

Scrape config in `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'astrovox-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboards

Import dashboards from `monitoring/grafana/`:

- Backend metrics (request rate, latency, errors)
- Database metrics (connections, query time)
- Redis metrics (hit rate, memory usage)
- AI usage metrics (requests per model, token usage)

### Alerts

Configure alerts in `monitoring/alerting/`:

- High error rate (> 5% 5xx)
- High latency (p99 > 2s)
- Low disk space (< 10%)
- Database connection exhaustion
- AI provider failures

---

## Security Hardening

1. **Secrets management** — Use Docker secrets or Kubernetes Secrets, never `.env` in production
2. **Network policies** — Restrict pod-to-pod communication in Kubernetes
3. **RBAC** — Least-privilege service accounts
4. **TLS everywhere** — Enforce HTTPS, disable HTTP
5. **Security headers** — CSP, HSTS, X-Frame-Options
6. **Dependency scanning** — Run `pip-audit` and `npm audit` in CI
7. **Image scanning** — Scan Docker images for vulnerabilities
8. **Audit logging** — Enable PostgreSQL audit logging
9. **Rate limiting** — Aggressive limits in production
10. **WAF** — Consider Cloudflare or AWS WAF for DDoS protection

---

## Troubleshooting

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| Backend 502 | Backend not ready | Check `/health/live`, pod logs |
| High latency | Database slow | Check connection pool, add indexes |
| Redis full | Memory pressure | Increase `maxmemory`, review TTLs |
| Rate limit errors | Traffic spike | Increase `RATE_LIMIT` or add caching |
| Auth failures | JWT secret mismatch | Verify `SECRET_KEY` across pods |
| Frontend blank | API URL wrong | Check `VITE_API_URL` in frontend build |

---

## Rollback

### Docker Compose

```bash
# Rollback to previous image
docker-compose up -d --force-recreate backend

# Or use specific tag
IMAGE_TAG=1.9.0 docker-compose up -d --build
```

### Kubernetes

```bash
# Undo rollout
kubectl rollout undo deployment/backend -n astrovox

# Check rollout status
kubectl rollout status deployment/backend -n astrovox
```

---

## Maintenance

### Database Migrations

```bash
# Check current version
cd 02-Backend && alembic current

# Apply pending migrations
cd 02-Backend && alembic upgrade head

# Rollback one migration
cd 02-Backend && alembic downgrade -1
```

### Dependency Updates

```bash
# Backend
cd 02-Backend
pip list --outdated
pip install --upgrade <package>
pip freeze > requirements.txt

# Frontend
npm outdated
npm update
```

### Log Rotation

Docker logging driver configured with rotation:
```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

Kubernetes: Use a DaemonSet with Fluentd or Vector for log aggregation.
