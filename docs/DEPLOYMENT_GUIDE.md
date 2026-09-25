# DEPLOYMENT_GUIDE

Deployment instructions: environment variables, secrets, database migrations, backup and restore, and rolling deploys.

## Prerequisites

- Docker & Docker Compose
- Supabase account (free tier works)
- At least one AI provider API key
- Domain name (for production)

## Quick Start (Docker)

```bash
git clone https://github.com/yourusername/AstrovoxAi.git
cd AstrovoxAi
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
