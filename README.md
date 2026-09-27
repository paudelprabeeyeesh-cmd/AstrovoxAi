# ASTROVOX AI

> Advanced AI Chat Platform — Multi-provider support, persistent memory, agent systems, enterprise-grade infrastructure, and cutting-edge AI research.

## What is AstrovoxAI?

AstrovoxAI is a production-ready AI chat platform that unifies multiple LLM providers (OpenAI, Anthropic, Google Gemini, Ollama, Groq) behind a single modern interface. It includes persistent conversation memory, streaming responses, RAG, autonomous agent tool-use, team workspaces, advanced safety systems, and comprehensive monitoring — deployable via Docker or Kubernetes.

## Key Features

- **Multi-provider AI chat** — OpenAI, Anthropic Claude, Google Gemini, Ollama (local models), Groq
- **Streaming responses** — Real-time SSE token streaming for all providers
- **Persistent AI memory** — Long-term user memory with importance weighting and auto-extraction
- **RAG pipeline** — Retrieval-Augmented Generation with vector embeddings
- **Autonomous agents** — Tool use, planning, multi-agent collaboration, safety guards
- **Team workspaces** — Shared conversations, folders, chat branching, real-time collaboration
- **Terminal console** — Interactive CLI for power users
- **Voice & multimodal** — Voice input/output, image understanding, code execution, audio transcription
- **Enterprise ready** — SSO (SAML/OIDC), RBAC, audit logging, SOC 2 controls, billing
- **Observability** — Prometheus metrics, Grafana dashboards, structured logging, distributed tracing
- **SDKs** — Python, TypeScript, Go, Rust SDKs with OpenAPI-generated clients
- **Extensible** — Plugin marketplace, webhooks, custom tools, IDE/browser extensions
- **AI Safety** — Prompt injection defense, content moderation, PII detection, red teaming
- **Advanced AI** — RLHF, Constitutional AI, distributed training, inference optimization
- **Robotics** — ROS2 integration, sensor fusion, simulation, manipulation
- **Quantum-ready** — Quantum simulation interfaces and quantum-safe cryptography

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

## Model Training, Inference & Evaluation

AstrovoxAI includes a complete LLM training and inference toolkit under `models/llm/`.

### Training

```bash
# Install ML dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Train a tiny model
python examples/train_tiny.py --config models/llm/configs/config_100m.yaml

# Fine-tune on instruction data
python examples/finetune.py --config models/llm/configs/config_finetune.yaml --model model.pt
```

### Inference

```bash
# Generate text
python examples/generate.py --prompt "Once upon a time" --checkpoint model.pt

# Start API server
python examples/serve_api.py --config models/llm/configs/config_4b.yaml --checkpoint model.pt --port 8000

# Run benchmarks
python examples/evaluate.py --checkpoint model.pt --benchmarks mmlu hellaswag
```

### Evaluation

```bash
# Quick eval (MMLU, HellaSwag, GSM8K, HumanEval, MBPP, PIQA, BoolQ, Winogrande)
python examples/evaluate.py --checkpoint model.pt --max-samples 500 --output eval_report.json
```

### Export

```bash
# Export to HuggingFace format
python examples/export_model.py --checkpoint model.pt --config models/llm/configs/config_4b.yaml --format huggingface --output-dir export/hf

# Export to ONNX
python examples/export_model.py --checkpoint model.pt --config models/llm/configs/config_4b.yaml --format onnx --output-dir export/onnx

# Export to GGUF
python examples/export_model.py --checkpoint model.pt --config models/llm/configs/config_4b.yaml --format gguf --output-dir export/gguf
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
├── models/                     # LLM model code
│   └── llm/
│       ├── model/              # Transformer architecture
│       ├── trainer/            # Pre-training and fine-tuning
│       ├── tokenizer/          # Tokenizer training
│       ├── inference/          # Generation engine + FastAPI server
│       ├── evaluation/         # Benchmark harness
│       ├── quantization.py     # INT8/FP16/BF16 quantization
│       ├── export.py           # Multi-format model export
│       └── configs/            # Model size configs
├── examples/                   # Developer examples
├── tests/                      # Model unit and integration tests
├── scripts/                    # Benchmark and utility scripts
├── docs/                       # Documentation
├── database/                   # Database schemas and migrations
├── frontend/                   # Legacy frontend assets
├── sdk/                        # Generated SDKs
├── charts/                     # Helm charts
├── k8s/                        # Kubernetes manifests
├── monitoring/                 # Prometheus/Grafana configs
├── docker-compose.yml          # Docker Compose (dev)
├── docker-compose.prod.yml     # Docker Compose (production)
├── Dockerfile.backend          # Backend Dockerfile
├── Dockerfile.frontend         # Frontend Dockerfile
├── Dockerfile.training         # Model training Dockerfile
├── Dockerfile.inference        # Inference server Dockerfile
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
| Safety | `02-Backend/app/safety_routes.py` | Safety and moderation endpoints |
| Training | `02-Backend/app/training/` | Model fine-tuning and RLHF |
| Analytics | `02-Backend/app/api/routers/analytics_route.py` | Usage analytics |
| Model | `models/llm/` | Transformer model, trainer, tokenizer, inference, quantization, export |

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

## Model API Reference

See [docs/api-reference/](docs/api-reference/) for detailed model API documentation:
- [Models](docs/api-reference/models.md) — LLM architecture and config
- [Tokenizer](docs/api-reference/tokenizer.md) — Tokenizer training and loading
- [Training](docs/api-reference/training.md) — Pre-training and fine-tuning APIs
- [Inference](docs/api-reference/inference.md) — Generation engines and server APIs
- [Evaluation](docs/api-reference/evaluation.md) — Benchmark harness
- [Quantization](docs/api-reference/quantization.md) — Quantization utilities
- [Export](docs/api-reference/export.md) — Multi-format model export

## Architecture Diagrams

See [docs/architecture/](docs/architecture/) for Mermaid diagrams:
- [Model Architecture](docs/architecture/model-architecture.md)
- [Training Pipeline](docs/architecture/training-pipeline.md)
- [Inference Pipeline](docs/architecture/inference-pipeline.md)

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
# Model tests
pytest tests/ -v

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

## Documentation

- **[docs/README.md](docs/README.md)** — Documentation index
- **[docs/API.md](docs/API.md)** — Complete REST API reference
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design and architecture
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Production deployment guide
- **[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)** — Contribution guidelines
- **[docs/agents.md](docs/agents.md)** — Autonomous agents guide
- **[docs/sdk.md](docs/sdk.md)** — SDK and CLI reference
- **[docs/extensions.md](docs/extensions.md)** — IDE and browser extensions
- **[docs/inference.md](docs/inference.md)** — Inference engine documentation
- **[docs/training.md](docs/training.md)** — Distributed training guide
- **[docs/safety.md](docs/safety.md)** — AI safety and alignment
- **[docs/robotics.md](docs/robotics.md)** — Robotics integration
- **[docs/enterprise.md](docs/enterprise.md)** — Enterprise platform features

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS errors | Check `ALLOWED_ORIGINS` includes your frontend URL |
| Provider not working | Verify API key is set in `.env` |
| Ollama not connecting | Ensure Ollama is running: `ollama serve` |
| Database errors | Run `database/schemas/supabase_setup.sql` in Supabase |
| Rate limit exceeded | Wait or increase `RATE_LIMIT` in `.env` |
| Import errors in backend | Ensure Python 3.9+ and install `requirements.txt` |
| CUDA out of memory | Reduce `batch_size` or enable `gradient_checkpointing` in config |

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
- [x] Enterprise SSO (SAML, OIDC)
- [x] Model training and inference toolkit
- [x] Quantization and export utilities

### Upcoming

- [ ] Multi-modal support (images, audio, video)
- [ ] Voice conversations with real-time transcription
- [ ] Plugin marketplace
- [ ] Team workspaces with real-time collaboration
- [ ] Advanced analytics dashboard
- [ ] Mobile apps (iOS, Android)
- [ ] Desktop app (Tauri)
- [ ] HIPAA-compliant deployment

## License

MIT License

## Authors

- **Prabesh Paudel** — Founder, CEO, CTO, Chief AI Architect
- **Dipson Baral** — Co-Founder
- **Ranjit Paudel** — Member of Astrovox
