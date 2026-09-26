# ASTROVOX AI

> Advanced AI Chat Platform — Multi-provider support, persistent memory, agent systems, and enterprise-grade infrastructure.

## What is AstrovoxAI?

AstrovoxAI is a production-ready AI chat platform that unifies multiple LLM providers (OpenAI, Anthropic, Google Gemini, Ollama) behind a single modern interface. It includes persistent conversation memory, streaming responses, RAG, autonomous agent tool-use, team workspaces, and comprehensive monitoring — deployable via Docker or Kubernetes.

## Key Features

- **Multi-provider AI chat** — OpenAI, Anthropic Claude, Google Gemini, Ollama (local models)
- **Streaming responses** — Real-time SSE token streaming for all providers
- **Persistent AI memory** — Long-term user memory with importance weighting
- **RAG pipeline** — Retrieval-Augmented Generation with embeddings
- **Autonomous agents** — Tool use, planning, multi-agent collaboration
- **Team workspaces** — Shared conversations, folders, chat branching
- **Terminal console** — Interactive CLI for power users
- **Voice & multimodal** — Voice input/output, image understanding, code execution
- **Enterprise ready** — SSO, RBAC, audit logging, SOC 2 controls, billing
- **Observability** — Prometheus metrics, Grafana dashboards, structured logging
- **SDKs** — Python and TypeScript SDKs with OpenAPI-generated clients
- **Extensible** — Plugin marketplace, webhooks, custom tools

## Supported AI Providers

| Provider | Models | Streaming |
|----------|--------|-----------|
| OpenAI | GPT-4, GPT-4o Mini, GPT-3.5 Turbo | Yes |
| Anthropic | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku | Yes |
| Google Gemini | Gemini 1.5 Pro, 1.5 Flash, 1.0 Pro | Yes |
| Ollama (Local) | Llama 3, Llama 3.1, Mistral, Mixtral, Code Llama, Phi-3, Gemma 2 | Partial |
| Groq | Various Groq-optimized models | Yes |

## Technology Stack

### Frontend
- React 18, Vite 6, TypeScript
- Tailwind CSS, Radix UI, Framer Motion
- Zustand, React Query, React Router
- Monaco Editor, KaTeX, Mermaid, Shiki

### Backend
- FastAPI, Python 3.9+
- Supabase (PostgreSQL + Auth + Row Level Security)
- Redis (caching, rate limiting, session store)
- Prometheus + Grafana (monitoring)

### Infrastructure
- Docker, Docker Compose
- Kubernetes (Helm charts)
- GitHub Actions (CI/CD)
- Nginx (reverse proxy, CDN)

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.9+
- Supabase account
- At least one AI provider API key

### Local Development

```bash
# Clone
git clone https://github.com/astrovox/astrovox.git
cd astrovox

# Install frontend dependencies
npm install

# Install backend dependencies
cd 02-Backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase and AI provider keys

# Run database migrations
# Execute database/schemas/supabase_setup.sql in Supabase SQL Editor

# Start backend (terminal 1)
cd 02-Backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (terminal 2)
npm run dev

# Open http://localhost:5173
```

### Docker

```bash
cp .env.example .env
# Edit .env
docker-compose up --build
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | Yes | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |
| `VITE_API_URL` | No | Backend API URL (default: http://localhost:8000) |
| `SUPABASE_URL` | Yes | Supabase project URL (backend) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `GEMINI_API_KEY` | No | Google Gemini API key |
| `GROQ_API_KEY` | No | Groq API key |
| `OLLAMA_BASE_URL` | No | Ollama server URL |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins |
| `RATE_LIMIT` | No | Rate limit (default: 120/minute) |
| `DAILY_AI_LIMIT` | No | Daily AI usage quota (default: 50) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |
| `ENVIRONMENT` | No | development, staging, production |

*At least one AI provider key is required.

## Project Structure

```
AstrovoxAi/
├── src/                        # React frontend (Vite + TypeScript)
│   ├── components/             # UI components
│   ├── hooks/                  # Custom React hooks
│   ├── services/               # Frontend services
│   ├── utils/                  # Utilities
│   ├── platform/               # Cross-platform code (PWA, offline)
│   ├── mobile/                 # Mobile adapters
│   ├── terminal/               # Terminal engine
│   ├── design/                 # Design system
│   ├── app.jsx                 # Main app component
│   ├── auth.jsx                # Authentication UI
│   ├── Chat.jsx                # Chat interface
│   ├── Sidebar.jsx             # Conversation sidebar
│   ├── MemoryPanel.jsx         # Memory management
│   ├── SettingsPanel.jsx       # User settings
│   ├── telemetry.jsx           # System telemetry
│   └── terminalconsole.jsx     # Terminal console
├── 02-Backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── api/                # API routers
│   │   ├── providers/          # AI provider implementations
│   │   ├── aios/               # AI Operating System
│   │   ├── agi_reasoning/      # AGI reasoning modules
│   │   ├── enterprise/         # Enterprise features
│   │   ├── billing/            # Billing & subscriptions
│   │   ├── analytics/          # Analytics engine
│   │   ├── middleware/         # Security & request middleware
│   │   ├── chat.py             # Chat routes
│   │   ├── memory.py           # Memory routes
│   │   ├── terminal.py         # Terminal routes
│   │   ├── embeddings_route.py # Embeddings API
│   │   ├── database.py         # Database operations
│   │   ├── metrics.py          # Prometheus metrics
│   │   └── providers/          # LLM provider adapters
│   └── tests/                  # Backend tests
├── database/                   # Database schemas and migrations
├── frontend/                   # Legacy frontend assets
├── docs/                       # Documentation
├── sdk/                        # Generated SDKs
├── charts/                     # Helm charts
├── k8s/                        # Kubernetes manifests
├── monitoring/                 # Prometheus/Grafana configs
├── docker-compose.yml          # Docker Compose (dev)
├── docker-compose.prod.yml     # Docker Compose (production)
├── Dockerfile.backend          # Backend Dockerfile
├── Dockerfile.frontend         # Frontend Dockerfile
├── Makefile                    # Build shortcuts
├── justfile                    # Task runner
└── package.json                # Frontend dependencies
```

## Major Backend Modules

| Module | Path | Description |
|--------|------|-------------|
| Chat | `02-Backend/app/chat.py` | Conversation and message management with streaming |
| Memory | `02-Backend/app/memory.py` | Persistent AI memory with importance weighting |
| Terminal | `02-Backend/app/terminal.py` | Interactive terminal console API |
| Embeddings | `02-Backend/app/embeddings_route.py` | Text vectorization via Gemini |
| Providers | `02-Backend/app/providers/` | OpenAI, Anthropic, Gemini, Ollama adapters |
| Auth | `02-Backend/app/services/auth/` | Supabase authentication |
| Enterprise | `02-Backend/app/enterprise/` | SSO, RBAC, billing, teams |
| Agents | `02-Backend/app/api/routers/agent_route.py` | Agent management and execution |
| RAG | `02-Backend/app/routers/rag.py` | Retrieval-Augmented Generation |
| Workspace | `02-Backend/app/api/routers/workspace_route.py` | Team workspaces and folders |
| Kernel | `02-Backend/app/kernel/` | Core AI kernel and orchestration |
| AIOS | `02-Backend/app/aios/` | AI Operating System runtime |

## API Overview

| Domain | Base Path |
|--------|-----------|
| Authentication | `/auth/*` |
| Chat | `/chat/*` |
| Memory | `/memory/*` |
| Terminal | `/api/terminal/*` |
| Embeddings | `/embeddings/*` |
| Agents | `/api/v1/agents/*` |
| Workspace | `/api/v1/workspace/*` |
| Enterprise | `/api/v1/enterprise/*` |
| Health | `/health*` |
| Metrics | `/metrics` |

Full API reference: [docs/API.md](docs/API.md)

## Database Schema

Core tables (Supabase PostgreSQL):

| Table | Purpose |
|-------|---------|
| `profiles` | User profiles linked to Supabase Auth |
| `conversations` | Chat conversations with model metadata |
| `messages` | Individual messages with token usage |
| `ai_memory` | Persistent memory entries with importance |
| `user_settings` | User preferences and AI settings |

All tables enforce Row Level Security (RLS) for tenant isolation.

## Testing

```bash
# Backend tests
cd 02-Backend
pytest

# Frontend lint
npm run lint

# Frontend typecheck
npm run typecheck

# Frontend tests
npm run test

# Full test suite
npm run test:all
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS errors | Check `ALLOWED_ORIGINS` includes your frontend URL |
| Provider not working | Verify API key is set in `.env` |
| Ollama not connecting | Ensure Ollama is running: `ollama serve` |
| Database errors | Run `database/schemas/supabase_setup.sql` in Supabase |
| Rate limit exceeded | Wait or increase `RATE_LIMIT` in `.env` |
| Import errors in backend | Ensure Python 3.9+ and install `requirements.txt` |

## Roadmap

See [docs/README.md](docs/README.md) for the full documentation index and [docs/roadmap.md](docs/roadmap.md) for strategic direction.

### Current Focus (v2.0.0)

- [x] Multi-provider AI support
- [x] Streaming responses via SSE
- [x] Persistent conversation memory
- [x] RAG with embeddings
- [x] Agent system with tool use
- [x] Docker and Kubernetes deployment
- [x] CI/CD pipeline
- [x] Monitoring and observability

### Upcoming

- [ ] Multi-modal support (images, audio, video)
- [ ] Voice conversations with real-time transcription
- [ ] Plugin marketplace
- [ ] Team workspaces with real-time collaboration
- [ ] Advanced analytics dashboard
- [ ] Mobile apps (iOS, Android)
- [ ] Desktop app (Tauri)
- [ ] Enterprise SSO (SAML, OIDC)
- [ ] HIPAA-compliant deployment

## License

MIT License

## Authors

- **Prabesh Paudel** — Founder, CEO, CTO, Chief AI Architect
- **Dipson Baral** — Co-Founder
- **Ranjit Paudel** — Member of Astrovox
