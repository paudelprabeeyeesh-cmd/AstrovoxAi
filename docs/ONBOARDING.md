# Developer Onboarding Checklist

Use this checklist to onboard new developers to the Astrovox AI project.

## Prerequisites

- [ ] Node.js 18+ installed (`node --version`)
- [ ] Python 3.9+ installed (`python --version`)
- [ ] Git installed (`git --version`)
- [ ] Docker & Docker Compose installed
- [ ] Supabase account created
- [ ] Code editor configured (VS Code recommended)

## Environment Setup

- [ ] Clone repository: `git clone https://github.com/astrovox/astrovox.git`
- [ ] Navigate to project: `cd astrovox`
- [ ] Install frontend dependencies: `npm install`
- [ ] Install backend dependencies: `cd 02-Backend && pip install -r requirements.txt`
- [ ] Copy environment file: `cp .env.example .env`
- [ ] Configure `.env` with required values
- [ ] Run pre-commit install: `pre-commit install`

## Database Setup

- [ ] Create Supabase project
- [ ] Execute `database/schemas/supabase_setup.sql` in Supabase SQL Editor
- [ ] Verify tables created: `profiles`, `conversations`, `messages`, `memories`
- [ ] Set `DATABASE_URL` in `.env`

## Local Development

- [ ] Start backend: `cd 02-Backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- [ ] Start frontend: `npm run dev`
- [ ] Open http://localhost:5173
- [ ] Sign up / log in
- [ ] Create a new chat
- [ ] Send a test message
- [ ] Verify streaming response works

## Verification

- [ ] Backend health check: `curl http://localhost:8000/health`
- [ ] API docs available: http://localhost:8000/docs
- [ ] Frontend loads without console errors
- [ ] Authentication works (signup/login/logout)
- [ ] AI provider responds to messages
- [ ] Conversation history persists on refresh

## Testing

- [ ] Run backend tests: `cd 02-Backend && pytest`
- [ ] Run frontend lint: `npm run lint`
- [ ] Run frontend typecheck: `npm run typecheck`
- [ ] Run frontend tests: `npm run test`

## Documentation Review

- [ ] Read [README.md](../README.md)
- [ ] Read [CONTRIBUTING.md](./CONTRIBUTING.md)
- [ ] Read [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- [ ] Read [SECURITY.md](./SECURITY.md)
- [ ] Review [API Reference](./API_REFERENCE.md)
- [ ] Review [Architecture](./ARCHITECTURE.md)

## Next Steps

- [ ] Join [Discord](https://discord.gg/astrovox)
- [ ] Introduce yourself in #introductions
- [ ] Pick up a good first issue
- [ ] Review [Roadmap](./ROADMAP.md)
