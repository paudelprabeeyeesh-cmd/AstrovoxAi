# Getting Started Checklist

Use this checklist to verify your Astrovox AI setup is complete and working.

## Prerequisites

- [ ] Node.js 18+ installed (`node --version`)
- [ ] Python 3.9+ installed (`python --version`)
- [ ] Git installed (`git --version`)
- [ ] Supabase account created
- [ ] At least one AI provider API key (OpenAI, Anthropic, Gemini, or Ollama)

## Installation

- [ ] Clone repository: `git clone https://github.com/astrovox/astrovox.git`
- [ ] Navigate to project: `cd astrovox`
- [ ] Install frontend dependencies: `npm install`
- [ ] Install backend dependencies: `cd 02-Backend && pip install -r requirements.txt`
- [ ] Copy environment file: `cp .env.example .env`
- [ ] Configure `.env` with required values

## Configuration

- [ ] Set `DATABASE_URL` in `.env`
- [ ] Set `SUPABASE_URL` in `.env`
- [ ] Set `SUPABASE_ANON_KEY` in `.env`
- [ ] Set `OPENAI_API_KEY` (or other provider keys) in `.env`
- [ ] Run Supabase SQL setup in SQL editor

## Database Setup

- [ ] Execute `database/schemas/supabase_setup.sql` in Supabase SQL Editor
- [ ] Verify tables created: `profiles`, `conversations`, `messages`, `memories`

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

## Docker Setup (Alternative)

- [ ] Docker & Docker Compose installed
- [ ] Run: `docker-compose up --build`
- [ ] Verify containers are healthy: `docker-compose ps`
- [ ] Access http://localhost:5173

## Next Steps

- [ ] Read [API Reference](./api-reference.md)
- [ ] Explore [Examples Gallery](./examples-gallery.md)
- [ ] Try [SDK Quickstart](./SDK_QUICKSTART.md)
- [ ] Review [Architecture Diagrams](./architecture-diagrams.md)
