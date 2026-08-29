# AstrovoxAI Quick Start Guide

Get AstrovoxAI up and running in 5 minutes.

## Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.9+ (for backend)
- **Docker** and **Docker Compose** (optional, for containerized setup)
- **Supabase Account** (free tier works)
- **OpenAI API Key** (optional, can use mock mode)

## Option 1: Docker Compose (Recommended - 2 minutes)

The fastest way to get started.

### 1. Clone and configure
```bash
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi
cp .env.example .env
```

### 2. Edit `.env` with your credentials
```bash
# Essential variables (minimum required)
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
OPENAI_API_KEY=sk-your-key-here
```

Get these from:
- **Supabase URL & Key**: [Supabase Dashboard](https://app.supabase.com) → Settings → API
- **OpenAI Key**: [OpenAI Platform](https://platform.openai.com/api-keys)

### 3. Start all services
```bash
docker-compose up --build
```

### 4. Access the application
- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

That's it! 🎉

## Option 2: Manual Setup (Linux/macOS - 5 minutes)

### 1. Clone repository
```bash
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi
cp .env.example .env
```

### 2. Backend setup
```bash
cd 02-Backend
python -m venv venv

# On Linux/macOS:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend setup (new terminal)
```bash
cd <project-root>
npm install
npm run dev
```

### 4. Access the application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Database Setup

### Automated (Recommended)
```bash
# Linux/macOS
bash scripts/setup-database.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/setup-database.ps1
```

### Manual
1. Go to [Supabase Dashboard](https://app.supabase.com) → SQL Editor
2. Run the SQL from `database/schemas/supabase_setup.sql`
3. Run migrations:
   - `database/migrations/0001_indexes_and_signup_trigger.sql`
   - `database/migrations/0002_telemetry_events.sql`

## Verify Installation

### 1. Backend Health
```bash
curl http://localhost:8000/health
# Expected: { "status": "OK" }
```

### 2. Frontend Health
```bash
curl http://localhost
# Expected: HTML response
```

### 3. API Documentation
Visit http://localhost:8000/docs to explore all available endpoints

### 4. Test Authentication
```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123",
    "username": "testuser"
  }'
```

## Common Commands

### Development
```bash
# Frontend development
npm run dev          # Start dev server
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run typecheck    # Type check TypeScript

# Backend development
cd 02-Backend
python -m uvicorn app.main:app --reload

# Run tests
pytest tests/ -v
```

### Docker Operations
```bash
# Start services
docker-compose up --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Reset everything
docker-compose down -v
```

### Database
```bash
# Auto setup (interactive)
bash scripts/setup-database.sh

# Connect to database
psql $DATABASE_URL
```

## Troubleshooting

### "Connection refused" on backend
- Ensure backend is running on port 8000
- Check if OPENAI_API_KEY is set
- Check logs: `docker-compose logs backend`

### Frontend can't connect to backend
- Verify `VITE_API_URL` in `.env` points to backend
- Check CORS settings: ensure frontend origin is in `ALLOWED_ORIGINS`
- Clear browser cache and hard refresh

### Database connection issues
- Verify Supabase credentials in `.env`
- Check if migrations have been run
- Confirm you have internet connection to Supabase
- Try resetting: `docker-compose down -v && docker-compose up`

### Port already in use
```bash
# Change ports in docker-compose.yml or .env
# Or free the ports:

# Linux/macOS
sudo lsof -ti:80,5173,8000 | xargs kill -9

# Windows PowerShell
Get-Process | Where-Object { $_.Name -like "*node*" -or $_.Name -like "*python*" } | Stop-Process
```

## Next Steps

1. **Create an account** at http://localhost
2. **Explore the dashboard** and memory features
3. **Test the chat API** at http://localhost:8000/docs
4. **Read the documentation**:
   - [API Documentation](./API.md)
   - [Architecture Overview](./Architecture.md)
   - [Deployment Guide](./DEPLOYMENT.md)
   - [Production Readiness](./PRODUCTION_READINESS.md)

## Features Included

✅ **Authentication** - Email/password signup and login  
✅ **Chat API** - Multi-turn conversation with streaming  
✅ **Memory System** - Short-term and long-term memory  
✅ **Telemetry** - Built-in event tracking and analytics  
✅ **Rate Limiting** - Protect against abuse  
✅ **Database** - PostgreSQL with RLS policies  
✅ **Security** - HTTP headers, input validation, CORS  
✅ **API Documentation** - Interactive Swagger UI  
✅ **Terminal Console** - Built-in system diagnostics  
✅ **Responsive UI** - Mobile-friendly React frontend  

## Project Structure

```
AstrovoxAi/
├── src/                    # Frontend (React + TypeScript)
│   ├── components/        # React components
│   ├── pages/            # Page components
│   └── styles/           # CSS/Tailwind
├── 02-Backend/           # Backend (FastAPI + Python)
│   └── app/
│       ├── main.py       # FastAPI application
│       ├── routes/       # API endpoints
│       └── models/       # Data models
├── database/             # Database schemas and migrations
│   ├── schemas/         # Initial schema
│   └── migrations/      # Migration files
├── docker-compose.yml    # Multi-container setup
├── Dockerfile.frontend   # Frontend Docker image
└── Dockerfile.backend    # Backend Docker image
```

## Support & Documentation

- **Issues**: [GitHub Issues](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/issues)
- **Discussions**: [GitHub Discussions](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/discussions)
- **API Docs**: http://localhost:8000/docs
- **Architecture**: [Architecture.md](./Architecture.md)
- **Deployment**: [DEPLOYMENT.md](./DEPLOYMENT.md)

## Configuration Reference

### Essential Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_SUPABASE_URL` | Supabase project URL | `https://abc123.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJ0...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MOCK_AI` | `false` | Use mock AI responses |
| `SECRET_KEY` | Generated | JWT secret key |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins |
| `DATABASE_URL` | Not set | Direct database connection |
| `REDIS_URL` | Not set | Redis cache connection |

See [.env.example](./.env.example) for complete list.

## Performance Tips

1. **Enable caching**: Set `REDIS_URL` for session caching
2. **Use CDN**: Deploy frontend to Vercel/Netlify
3. **Database indexes**: Ensure migrations are run
4. **Rate limiting**: Already configured, monitor `/api/stats`

## License

MIT License - see [LICENSE](./LICENSE) for details

---

**Ready?** Start with Docker Compose:
```bash
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi && cp .env.example .env
# Edit .env with your keys
docker-compose up --build
```

Then visit http://localhost to get started! 🚀
