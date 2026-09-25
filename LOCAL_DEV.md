# AstrovoxAI — Local Development Guide

## Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 14+ (or use Docker)
- Redis (optional, for caching)
- Git

## Quick Start (Windows)

### Option 1: Automated Setup
1. Double-click scripts/setup_local.bat
2. Wait for dependencies to install
3. Double-click scripts/run_local.bat
4. Open http://localhost:3000

### Option 2: Manual Setup

#### Backend
`ash
# 1. Clone repo
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
cd 02-Backend
pip install -r requirements.txt

# 4. Set environment variables
copy ..\.env.example ..\.env
# Edit .env with your values

# 5. Start PostgreSQL and Redis
# Using Docker:
docker run -d -p 5432:5432 -e POSTGRES_USER=astrovox -e POSTGRES_PASSWORD=astrovox -e POSTGRES_DB=astrovox postgres:16
docker run -d -p 6379:6379 redis:7-alpine

# 6. Run migrations
alembic upgrade head

# 7. Start backend
python -m uvicorn app.main:app --reload --port 8000
`

#### Frontend
`ash
# 1. Open new terminal
cd AstrovoxAi/apps/web

# 2. Install dependencies
npm install

# 3. Set environment variables
copy .env.example .env.local
# Edit .env.local with your values

# 4. Start frontend
npm run dev
`

## Quick Start (Mac/Linux)

`ash
# 1. Clone repo
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi

# 2. Run setup script
chmod +x scripts/*.sh
./scripts/setup_local.sh

# 3. Start PostgreSQL and Redis
docker run -d -p 5432:5432 -e POSTGRES_USER=astrovox -e POSTGRES_PASSWORD=astrovox -e POSTGRES_DB=astrovox postgres:16
docker run -d -p 6379:6379 redis:7-alpine

# 4. Start backend
cd 02-Backend
source ../venv/bin/activate  # if using venv
export DATABASE_URL=postgresql://astrovox:astrovox@localhost:5432/astrovox
export REDIS_URL=redis://localhost:6379/0
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000

# 5. Start frontend (new terminal)
cd apps/web
npm install
npm run dev
`

## Environment Variables

### Backend (.env in 02-Backend/)
`
DATABASE_URL=postgresql://astrovox:astrovox@localhost:5432/astrovox
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
MISTRAL_API_KEY=your_key_here
HF_API_KEY=your_key_here
STRIPE_SECRET_KEY=your_key_here
STRIPE_WEBHOOK_SECRET=your_secret_here
JWT_SECRET_KEY=your_jwt_secret_here_make_it_long_and_random
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
PYTHON_VERSION=3.12.0
`

### Frontend (apps/web/.env.local)
`
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your_nextauth_secret_here
NEXTAUTH_URL=http://localhost:3000
OPENAI_API_KEY=your_key_here
STRIPE_PUBLISHABLE_KEY=your_key_here
`

## Access Points
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics

## Useful Commands

### Backend
`ash
# Run with auto-reload
python -m uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v

# Run security scan
bandit -r app -ll

# Format code
black app/

# Type check
mypy app/
`

### Frontend
`ash
# Development
npm run dev

# Build
npm run build

# Start production
npm start

# Lint
npm run lint

# Type check
npm run typecheck
`

### Database
`ash
# Create migration
alembic revision --autogenerate -m  description

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
`

## Troubleshooting

### Backend won't start
- Check PostgreSQL is running: pg_isready -h localhost -p 5432
- Check DATABASE_URL is correct
- Check all required env vars are set

### Frontend won't start
- Check Node.js version: 
ode --version (need 18+)
- Delete node_modules and reinstall: m -rf node_modules && npm install
- Check .env.local exists

### Port already in use
- Change port: uvicorn app.main:app --reload --port 8001
- Or kill process: 	askkill /F /PID <pid> (Windows) or kill -9 <pid> (Mac/Linux)

### Database connection errors
- Verify PostgreSQL is running
- Check DATABASE_URL format: postgresql://user:pass@host:port/db
- Ensure database exists: createdb astrovox or via psql

## Docker Alternative
If you don't want to install dependencies locally:
`ash
# Build and run with Docker
docker build -t astrovox .
docker run -p 8000:8000 --env-file .env astrovox
`
