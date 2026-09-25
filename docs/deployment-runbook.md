# Deployment Runbook

Step-by-step deployment procedures for Astrovox AI across environments.

## Environments

- **Development**: Local machine, hot reload enabled
- **Staging**: Mirror of production for testing
- **Production**: Live environment with high availability

## Pre-Deployment Checklist

- [ ] All tests pass: `npm run test:all`
- [ ] Lint passes: `npm run lint`
- [ ] Typecheck passes: `npm run typecheck`
- [ ] Docker images built successfully
- [ ] Environment variables configured in deployment target
- [ ] Database migrations reviewed and ready
- [ ] Secrets rotated if compromised
- [ ] Monitoring dashboards configured

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `OPENAI_API_KEY` | OpenAI API key |
| `JWT_SECRET_KEY` | JWT signing secret |

### Optional

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GROQ_API_KEY` | Groq API key |
| `OLLAMA_BASE_URL` | Ollama server URL |
| `REDIS_URL` | Redis connection string |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret |

## Deployment Procedures

### Docker Compose

```bash
# Pull latest images
docker-compose pull

# Build and start
docker-compose up --build -d

# Verify health
curl http://localhost:8000/health
curl http://localhost:5173
```

### Kubernetes

```bash
# Apply configurations
kubectl apply -f k8s/

# Verify pods
kubectl get pods -n astrovox

# Check rollout status
kubectl rollout status deployment/astrovox-backend -n astrovox
kubectl rollout status deployment/astrovox-frontend -n astrovox
```

### Manual Server

```bash
# Backend
cd 02-Backend
pip install -r requirements.txt --upgrade
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
npm install
npm run build
npm run preview
```

## Post-Deployment Verification

- [ ] Health endpoint returns 200: `GET /health`
- [ ] Detailed health OK: `GET /health/detailed`
- [ ] Frontend loads successfully
- [ ] Authentication flow works
- [ ] AI providers respond
- [ ] Database connections healthy
- [ ] Logs show no errors
- [ ] Metrics exporting to Prometheus
- [ ] Alerts configured in Grafana

## Rollback Procedure

```bash
# Docker Compose
docker-compose down
docker-compose up --build -d --force-recreate --renew-anon-volumes

# Kubernetes
kubectl rollout undo deployment/astrovox-backend -n astrovox
kubectl rollout undo deployment/astrovox-frontend -n astrovox

# Database rollback
cd 02-Backend
alembic downgrade -1
```

## Database Migrations

```bash
# Run migrations
cd 02-Backend
alembic upgrade head

# Verify migration
alembic current

# Rollback if needed
alembic downgrade -1
```

## Secrets Rotation

1. Generate new secret in deployment target
2. Update environment variable
3. Restart affected services
4. Verify functionality
5. Revoke old secret

## Monitoring

- **Grafana**: http://grafana.internal/d/astrovox
- **Prometheus**: http://prometheus.internal:9090
- **Logs**: `kubectl logs -f deployment/astrovox-backend -n astrovox`
- **Alerts**: Configured via Alertmanager

## Emergency Contacts

- On-call engineer: Check PagerDuty rotation
- Security issues: security@astrovox.ai
- Infrastructure: devops@astrovox.ai
