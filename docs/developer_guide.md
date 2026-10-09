# Developer Guide

## Overview

This guide helps developers set up, extend, and contribute to the AstrovoxAI platform.

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16+
- Redis 7+
- Git

## Project Structure

```
AstrovoxAi/
├── 02-Backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entrypoint
│   │   ├── routers/             # API route modules
│   │   ├── core/                # Logging, tracing, metrics
│   │   ├── security_headers.py  # Security middleware
│   │   ├── auth.py              # Authentication helpers
│   │   ├── database.py          # Supabase/PostgreSQL access
│   │   ├── chat.py              # Chat orchestration
│   │   ├── memory.py            # Memory management
│   │   └── rag/                 # Retrieval-augmented generation
│   ├── tests/                   # Pytest suites
│   ├── alembic/                 # DB migrations
│   └── Dockerfile.backend
├── frontend/
│   └── apps/web/                # Next.js frontend
├── docs/                        # Documentation root
├── docker-compose.yml
└── k8s/                         # Kubernetes manifests
```

## Local Development Setup

### 1. Clone and Environment

```bash
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi
cp .env.example .env
```

### 2. Start Infrastructure

```bash
docker compose up -d postgres redis
```

### 3. Backend

```bash
cd 02-Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend/apps/web
npm install
npm run dev
```

## Key Concepts

### Authentication

All protected endpoints require a Bearer token obtained via `/auth/login`. Tokens are stored in HTTP-only cookies for web clients.

### Rate Limiting

SlowAPI enforces per-IP limits. Default: `120/minute`. Configure via `RATE_LIMIT`.

### LLM Routing

The `LLMClient` in `app/core/llm.py` routes requests to providers (OpenAI, Anthropic, Gemini, Groq, Ollama) based on model selection and availability.

### Memory System

Short-term conversation memory is stored in PostgreSQL. Long-term memory uses pgvector embeddings for semantic search.

## Testing

```bash
# Backend
cd 02-Backend
pytest tests/ -v

# Frontend
cd frontend/apps/web
npm run test
```

## Code Style

- Python: `ruff` + `black`
- TypeScript: `eslint` + `prettier`
- Max line length: 120

## Debugging

```bash
# Backend logs
kubectl logs -f deployment/astrovox-backend -n astrovox --tail=100

# Database queries
kubectl exec -it <pod> -n astrovox -- psql -U astrovox -d astrovox

# Redis
kubectl exec -it <pod> -n astrovox -- redis-cli monitor
```
