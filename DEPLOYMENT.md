# ASTRAVOX PRIME - Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Supabase project with database configured
- OpenAI API key
- Domain name (for production deployment)

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# Supabase Configuration
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=_supabase_anon_key

# Backend Configuration
VITE_API_URL=http://localhost:8000

# OpenAI Configuration
OPENAI_API_KEY _openai_api_key

# Backend CORS (comma-separated list of allowed frontend origins)
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# App Settings
USE_MOCK_AI=false
SECRET_KEY=2068/07/16
```

## Database Setup

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Run the SQL from `database/schemas/supabase_setup.sql`
4. Run the migration from `database/migrations/0001_indexes_and_signup_trigger.sql`
5. Run the migration from `database/migrations/0002_telemetry_events.sql`

**Automated Database Setup (Optional):**
- **Linux/macOS**: `bash scripts/setup-database.sh`
- **Windows PowerShell**: `powershell -ExecutionPolicy Bypass -File scripts/setup-database.ps1`

This will create all necessary tables with RLS policies and performance indexes.

## Local Development

### Using Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

The application will be available at:
- Frontend: http://localhost:80
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup

#### Backend

```bash
cd 02-Backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

## Production Deployment

### Option 1: Docker Compose (Single Server)

1. Update `.env` with production values
2. Update `ALLOWED_ORIGINS` with your production domain
3. Build and deploy:

```bash
docker-compose -f docker-compose.yml up -d
```

### Option 2: Separate Containers (Recommended)

#### Backend Deployment

```bash
# Build backend image
docker build -f Dockerfile.backend -t astravox-backend:latest .

# Run backend container
docker run -d \
  --name astravox-backend \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  astravox-backend:latest
```

#### Frontend Deployment

```bash
# Build frontend image
docker build -f Dockerfile.frontend -t astravox-frontend:latest .

# Run frontend container
docker run -d \
  --name astravox-frontend \
  -p 80:80 \
  --link astravox-backend:backend \
  --restart unless-stopped \
  astravox-frontend:latest
```

### Option 3: Cloud Platforms

#### Vercel (Frontend) + Railway/Render (Backend)

**Frontend (Vercel):**

1. Connect your GitHub repository to Vercel
2. Set environment variables in Vercel dashboard:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_API_URL` (backend URL)
3. Deploy

**Backend (Railway/Render):**

1. Connect your GitHub repository to Railway/Render
2. Set environment variables:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `OPENAI_API_KEY`
   - `ALLOWED_ORIGINS` (your Vercel domain)
   - `SECRET_KEY`
3. Deploy

#### AWS/GCP/Azure

For major cloud providers, consider using:
- **EKS/GKE/AKS** for container orchestration
- **RDS/Cloud SQL** for managed PostgreSQL (if not using Supabase)
- **Load balancers** for high availability
- **CDN** for static asset delivery

## Health Checks

The application includes health check endpoints:

- Backend: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/health/readiness`
- Liveness: `http://localhost:8000/health/liveness`

## Monitoring

### Logs

```bash
# Docker Compose
docker-compose logs -f backend
docker-compose logs -f frontend

# Individual containers
docker logs -f astravox-backend
docker logs -f astravox-frontend
```

### Metrics

The backend includes telemetry endpoints:
- `GET /api/stats` - User statistics
- `GET /health` - Service health status

## Security Considerations

1. **Environment Variables**: Never commit `.env` files. Use secret management in production.
2. **CORS**: Configure `ALLOWED_ORIGINS` to only include your production domains.
3. **Rate Limiting**: Rate limits are configured on sensitive endpoints:
   - Signup: 5 requests/minute
   - Login: 10 requests/minute
   - Chat messages: 30 requests/minute
4. **SSL/TLS**: Use HTTPS in production. Configure SSL certificates on your load balancer or reverse proxy.
5. **Database**: Ensure Supabase RLS policies are properly configured.
6. **API Keys**: Rotate OpenAI and Supabase keys regularly.

## Scaling

### Horizontal Scaling

For high-traffic deployments:

1. **Backend**: Deploy multiple instances behind a load balancer
2. **Frontend**: Use CDN for static assets, multiple web servers
3. **Database**: Use connection pooling, consider read replicas

### Vertical Scaling

- **Backend**: Increase CPU/RAM based on load
- **Frontend**: Typically lightweight, scale based on traffic

## Troubleshooting

### Backend won't start

- Check environment variables are set
- Verify Supabase credentials are correct
- Check logs for specific error messages

### Frontend can't connect to backend

- Verify CORS settings in `ALLOWED_ORIGINS`
- Check backend is running and accessible
- Verify `VITE_API_URL` is correct

### Database connection issues

- Verify Supabase project is active
- Check database migration was run
- Verify RLS policies are configured

## Backup and Recovery

### Database Backups

Supabase provides automatic backups. For additional safety:

1. Enable point-in-time recovery in Supabase
2. Export regular SQL dumps
3. Store backups in secure, off-site location

### Application Backups

- Backup `.env` file securely
- Version control application code
- Document any custom configurations

## Performance Optimization

1. **Database**: Ensure indexes are created (migration 0001)
2. **Caching**: Consider Redis for session caching
3. **CDN**: Use CDN for static assets in production
4. **Compression**: Enable gzip compression (configured in nginx.conf)
5. **Bundle Size**: Monitor and optimize frontend bundle size

## Support

For deployment issues:
1. Check logs for error messages
2. Review this deployment guide
3. Consult API documentation
4. Open an issue on GitHub with detailed error information

## Pre-Deployment Checklist

Before deploying to production, verify the following:

### Environment & Credentials
- [ ] `.env` file created with all required variables
- [ ] OpenAI API key is valid and has sufficient quota
- [ ] Supabase project is created and accessible
- [ ] Supabase connection string obtained from dashboard
- [ ] Database migrations have been run successfully
- [ ] All API keys are rotated from development values

### Backend Verification
```bash
cd 02-Backend
npm run build        # Verify build succeeds
npm run typecheck    # Verify TypeScript
npm run lint         # Verify linting
pytest tests/        # Run unit tests
```

### Frontend Verification
```bash
npm run lint         # Verify linting
npm run typecheck    # Verify TypeScript
npm run build        # Build production bundle
# Verify bundle size: dist/ should be ~100-120KB gzipped
```

### Health Checks
```bash
# After starting backend
curl http://localhost:8000/health
curl http://localhost:8000/health/readiness
curl http://localhost:8000/health/liveness

# After starting frontend
curl http://localhost:80
# Should return HTML

# Verify API connection
curl http://localhost:8000/docs  # Should return Swagger UI
```

### Database Verification
```bash
# Connect to your Supabase database and verify tables exist:
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

# Expected tables:
# - users
# - conversations
# - memory_entries
# - settings
# - usage
# - telemetry_events
```

### Security Verification
- [ ] HTTPS/SSL enabled in production
- [ ] CORS settings configured for your domain only
- [ ] Rate limiting is active
- [ ] Database RLS policies are enabled
- [ ] Security headers are present (CSP, HSTS, X-Frame-Options)
- [ ] No hardcoded secrets in environment
- [ ] API keys stored in secure secret manager

## Production Deployment Verification

After deploying to production, verify:

### 1. Frontend Accessibility
```bash
# Check that frontend is accessible
curl -I https://your-domain.com
# Should return 200 OK with appropriate headers
```

### 2. Backend Health
```bash
# Check backend health endpoints
curl https://your-domain.com/api/health
# Should return: { "status": "OK" }

curl https://your-domain.com/api/health/readiness
# Should return: { "status": "ready" }
```

### 3. Authentication
```bash
# Test signup
curl -X POST https://your-domain.com/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Test login
curl -X POST https://your-domain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

### 4. API Functionality
```bash
# Test chat endpoint
curl -X POST https://your-domain.com/api/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'

# Test telemetry
curl -X POST https://your-domain.com/telemetry/event \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_name":"test","category":"debug"}'
```

### 5. Database Connectivity
```bash
# Check database statistics
curl https://your-domain.com/api/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Post-Deployment Monitoring

### Essential Metrics to Monitor
- Backend response time (target: <200ms p95)
- Error rate (target: <0.1%)
- Database connection pool usage
- API rate limit violations
- Telemetry event throughput
- Frontend bundle load time (target: <2s)

### Recommended Monitoring Tools
- **Application Performance**: Sentry, New Relic, or DataDog
- **Infrastructure**: Prometheus + Grafana
- **Logging**: ELK Stack or CloudWatch
- **Uptime Monitoring**: Pingdom, Uptime Robot

### Log Inspection
```bash
# Watch backend logs
docker-compose logs -f backend

# Check for errors
docker-compose logs backend | grep ERROR

# Check telemetry events
curl https://your-domain.com/telemetry/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## License

This project is licensed under the MIT License.
