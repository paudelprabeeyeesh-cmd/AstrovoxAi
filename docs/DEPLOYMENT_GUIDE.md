# Deployment Guide

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
```

## Security

- Rotate secrets regularly
- Use HTTPS in production
- Enable rate limiting
- Review security headers
- Scan dependencies for vulnerabilities
