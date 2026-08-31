# ASTROVOX AI — DEPLOYMENT GUIDE

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

```env
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=sk-your-key

# Optional
ANTHROPIC_API_KEY=your_key
GEMINI_API_KEY=your_key
REDIS_URL=redis://localhost:6379
ALLOWED_ORIGINS=https://yourdomain.com
RATE_LIMIT=120/minute
LOG_LEVEL=INFO
```

## Database Setup

1. Create a Supabase project
2. Run `database/schemas/supabase_setup.sql` in the SQL editor
3. Run migrations in `database/migrations/`

## Production Deployment

### Fly.io

```bash
flyctl launch
flyctl secrets set OPENAI_API_KEY=sk-...
flyctl deploy
```

### Railway

1. Connect GitHub repo
2. Add environment variables
3. Deploy automatically on push

### Render

1. Create new Web Service
2. Connect GitHub repo
3. Set build command: `pip install -r requirements.txt && cd 02-Backend`
4. Set start command: `cd 02-Backend && uvicorn app.main:app --host 0.0.0.0 --port 8000`

### VPS (Ubuntu)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone and deploy
git clone https://github.com/yourusername/AstrovoxAi.git
cd AstrovoxAi
nano .env  # Add your values
docker-compose -f docker-compose.yml up -d
```

## SSL/TLS

Use Let's Encrypt with Nginx:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Monitoring

Access Prometheus at `:9090` and Grafana at `:3000`.

## Backup Strategy

```bash
# Database (Supabase handles this automatically)
# Files
tar -czf backup-$(date +%Y%m%d).tar.gz storage/
```

## Scaling

- Add Redis for caching and session storage
- Use a load balancer for multiple backend instances
- Enable database connection pooling
- Use CDN for static assets
