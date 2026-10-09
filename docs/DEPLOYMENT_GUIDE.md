# Deployment Guide

<<<<<<< HEAD
Deployment instructions: environment variables, secrets, database migrations, backup and restore, and rolling deploys.

## Prerequisites

- Docker & Docker Compose
- Supabase account (free tier works)
- At least one AI provider API key
- Domain name (for production)

## Quick Start (Docker)

```bash
git clone https://github.com/astrovox/astrovox.git
cd astrovox
cp .env.example .env
# Edit .env with your values
docker-compose up --build
```

## Environment Variables

See `.env.example` for all available options.

### Required

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET_KEY` - Secret key for JWT signing
- `OPENAI_API_KEY` - OpenAI API key

### Optional

- `ANTHROPIC_API_KEY` - Anthropic API key
- `GROQ_API_KEY` - Groq API key
- `GEMINI_API_KEY` - Google Gemini API key
- `STRIPE_SECRET_KEY` - Stripe API key
- `ALLOWED_ORIGINS` - Comma-separated CORS origins
- `ENVIRONMENT` - development, staging, production

## Database Migrations

```bash
cd 02-Backend
alembic upgrade head
```

## Health Checks

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health check
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe
- `GET /metrics` - Prometheus metrics
- `GET /alerts` - Active alerts

## Scaling

- Use a load balancer for multiple backend instances
- Enable database connection pooling
- Use CDN for static assets

## Production Deployment

### Docker Compose (Production)

```bash
docker-compose -f docker-compose.prod.yml up --build -d
```

### Kubernetes

```bash
kubectl apply -f k8s/
```

### Environment Setup

1. Set `ENVIRONMENT=production`
2. Configure `ALLOWED_ORIGINS` with your domain
3. Enable HTTPS with valid TLS certificates
4. Set up log aggregation (e.g., ELK, Datadog)
5. Configure backup schedules for database

## Backup and Restore

### Database Backup

```bash
pg_dump $DATABASE_URL > backup.sql
```

### Database Restore

```bash
psql $DATABASE_URL < backup.sql
```

## Rolling Deploys

Use Kubernetes rolling updates or Docker Swarm rolling updates to ensure zero-downtime deployments.

```yaml
# kubernetes/deployment.yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1
=======
## Environments

| Environment | Branch | URL | Auto-Deploy |
|-------------|--------|-----|-------------|
| Production | main (tags) | https://astrovox.ai | Yes |
| Staging | develop | https://staging.astrovox.ai | Yes |
| Preview | PRs | https://pr-*.astrovox.ai | Yes |

## Prerequisites

- Docker 24+ and Docker Compose v2.20+
- Python 3.12, Node.js 20, npm 9+
- kubectl configured for EKS clusters
- AWS CLI with EKS access
- GitHub secrets: `AWS_ROLE_ARN`, `GITHUB_TOKEN`

## Environment Variables

Required for all environments:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `SECRET_KEY` | JWT signing secret (256-bit min) | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | Yes |
| `ENVIRONMENT` | `production`, `staging`, or `development` | Yes |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | No (default: INFO) |
| `RATE_LIMIT` | Rate limit string (e.g. `120/minute`) | No (default: 120/minute) |
| `DAILY_AI_LIMIT` | Daily AI request limit per user | No (default: 50) |

Optional:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `GOOGLE_GENERATIVEAI_API_KEY` | Google Generative AI key |
| `NEO4J_URI` | Neo4j bolt URI |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `JAEGER_URL` | Jaeger collector endpoint |
| `METRICS_ENABLED` | Enable Prometheus metrics (`true`/`false`) |

## Local Development

```bash
# Clone and install
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi

# Copy environment file
cp .env.example .env
# Edit .env with your values

# Start full stack
docker compose up -d

# Verify
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

## Docker Build

```bash
# Build all services
docker compose build

# Build specific service
docker compose build backend

# Run with production overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d
```

## Kubernetes Deployment

### Prerequisites

```bash
# Configure EKS access
aws eks update-kubeconfig --name astrovox-prod --region us-east-1

# Verify access
kubectl cluster-info
kubectl get ns
```

### Deploy to Staging

```bash
# Staging deploys automatically on push to develop
# Manual deploy:
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ -n astrovox
kubectl rollout status deployment/astrovox-backend -n astrovox --timeout=5m
kubectl rollout status deployment/astrovox-frontend -n astrovox --timeout=5m
```

### Deploy to Production

```bash
# Production deploys on version tags (v*.*.*)
git tag v1.2.3
git push origin v1.2.3

# Or trigger manually via GitHub Actions workflow_dispatch
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ -n astrovox
kubectl rollout status deployment/astrovox-backend -n astrovox --timeout=10m
kubectl rollout status deployment/astrovox-frontend -n astrovox --timeout=10m
```

### Verify Deployment

```bash
kubectl get pods -n astrovox
kubectl get services -n astrovox
kubectl get ingress -n astrovox
kubectl get hpa -n astrovox
kubectl get events -n astrovox --sort-by='.lastTimestamp'
```

### Smoke Tests

```bash
# Backend health
kubectl run smoke-test --rm -i --restart=Never --image=curlimages/curl:latest -- \
  curl -f https://api.astrovox.ai/health

# Frontend health
kubectl run smoke-test-frontend --rm -i --restart=Never --image=curlimages/curl:latest -- \
  curl -f https://astrovox.ai/

# Metrics endpoint
kubectl run smoke-test-metrics --rm -i --restart=Never --image=curlimages/curl:latest -- \
  curl -f https://api.astrovox.ai/metrics
```

## Helm Chart

```bash
# Install with Helm
helm repo add astrovox https://charts.astrovox.ai
helm install astrovox astrovox/astrovox \
  --namespace astrovox \
  --create-namespace \
  --set image.tag=1.2.3 \
  --set secret.data.OPENAI_API_KEY=sk-...

# Upgrade
helm upgrade astrovox astrovox/astrovox \
  --namespace astrovox \
  --set image.tag=1.2.4
```

## Rollback

### Kubernetes Rollback

```bash
# Undo rollout
kubectl rollout undo deployment/astrovox-backend -n astrovox
kubectl rollout undo deployment/astrovox-frontend -n astrovox

# Rollout status
kubectl rollout status deployment/astrovox-backend -n astrovox
kubectl rollout status deployment/astrovox-frontend -n astrovox
```

### Helm Rollback

```bash
helm rollback astrovox -n astrovox
```

### Database Migrations

```bash
# Forward migration (preferred)
alembic upgrade head

# Rollback migration (use only if necessary)
alembic downgrade -1
```

## Monitoring

Access dashboards:

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | https://grafana.astrovox.ai | Admin (see GRAFANA_PASSWORD) |
| Prometheus | https://prometheus.astrovox.ai | Internal only |
| Jaeger | https://jaeger.astrovox.ai | Internal only |

## Logs

```bash
# Backend logs
kubectl logs -f deployment/astrovox-backend -n astrovox --tail=100

# Frontend logs
kubectl logs -f deployment/astrovox-frontend -n astrovox --tail=100

# Previous container logs
kubectl logs -f deployment/astrovox-backend -n astrovox --tail=100 --previous

# Filter by label
kubectl logs -l app=astrovox-backend -n astrovox --tail=100
```

## Troubleshooting

### Pods not starting

```bash
kubectl describe pod <pod-name> -n astrovox
kubectl get events -n astrovox --sort-by='.lastTimestamp'
```

### Image pull errors

```bash
# Check image exists
kubectl get deployment astrovox-backend -n astrovox -o jsonpath='{.spec.template.spec.containers[0].image}'

# If using private registry, verify imagePullSecret
kubectl get secret -n astrovox
```

### Ingress not working

```bash
kubectl describe ingress astrovox-ingress -n astrovox
kubectl get events -n astrovox --field-selector involvedObject.kind=Ingress
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
```

## Security

<<<<<<< HEAD
- Rotate secrets regularly
- Use HTTPS in production
- Enable rate limiting
- Review security headers
- Scan dependencies for vulnerabilities
=======
- All containers run as non-root users
- Read-only root filesystems where possible
- Network policies restrict pod-to-pod communication
- Secrets managed via Kubernetes Secrets (external secrets manager recommended)
- Images scanned with Trivy in CI
- SBOM generated for all images
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
