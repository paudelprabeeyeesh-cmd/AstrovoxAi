<<<<<<< HEAD
# ASTRAVOX AI 🚀
=======
# ASTRAVOX Ai 
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838

## Advanced AI Chat Platform 🚀

<<<<<<< HEAD
ASTRAVOX AI is a cutting-edge AI chat platform with multi-provider support, featuring a modern React frontend, a robust FastAPI backend, and Supabase for database and authentication. The platform supports streaming responses, AI memory, embeddings, telemetry, and an interactive terminal console.
=======
ASTRAVOX Ai is a cutting-edge AI chat platform designed to provide an intelligent and interactive conversational experience. It features a modern React frontend, a robust FastAPI backend, and leverages Supabase for its database and authentication needs. The platform is built with scalability and maintainability in mind, ensuring a seamless experience for users and developers alike.
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838

## Features 

<<<<<<< HEAD
- **User Authentication**: Secure sign-up, login, logout, and password reset via Supabase Auth
- **Multi-Provider AI Chat**: Support for OpenAI, Anthropic (Claude), Google Gemini, and Ollama (local models)
- **Streaming Responses**: Real-time token streaming for all supported providers
- **AI Memory System**: Persistent memory that provides context-aware responses
- **Embeddings API**: Text vectorization via Gemini Embedding API with batch support
- **Conversation History**: All messages saved and loadable for future reference
- **Interactive Terminal Console**: Command-line interface for system interactions
- **Telemetry**: Real-time system diagnostics and statistics
- **Rate Limiting**: Per-IP and per-endpoint rate limiting
- **Security Headers**: CSP, HSTS, XSS protection, and more
- **Docker Support**: Containerized deployment with Docker Compose
- **CI/CD Pipeline**: Automated testing, linting, and security scanning via GitHub Actions
=======
- **User Authentication**: Secure sign-up, login, logout, and password reset functionalities powered by Supabase Auth.
- **Persistent Sessions**: Users remain logged in across sessions, providing a continuous experience.
- **Protected Routes**: Ensures that only authenticated users can access sensitive parts of the application.
- **AI Chat Interface**: A dynamic chat environment where users can interact with an AI, create new conversations, and review past interactions.
- **Conversation History**: All messages and conversations are saved and can be loaded for future reference.
- **AI Memory System**: An intelligent memory system that stores important information from conversations, allowing the AI to provide more personalized and context-aware responses.
- **Dashboard**: A comprehensive dashboard featuring:
    - **Sidebar**: For managing and navigating between conversations.
    - **Telemetry**: Real-time system diagnostics and statistics.
    - **Terminal Console**: An interactive command-line interface for system interactions.
    - **Memory Panel**: To view and manage AI memory entries.
    - **Settings Panel**: For user-specific configurations, including AI model preferences and theme settings.
- **Responsive UI**: Designed to provide an optimal viewing and interaction experience across a wide range of devices.
- **Modular Backend**: A FastAPI backend with a clear, modular architecture for easy development and maintenance.
- **Supabase Integration**: Utilizes Supabase for PostgreSQL database, authentication, and real-time capabilities.
- **Rate Limiting**: Built-in rate limiting for authentication and chat endpoints to prevent abuse.
- **Docker Support**: Containerized deployment with Docker and Docker Compose for easy production deployment.
- **CI/CD Pipeline**: Automated testing, linting, and security scanning via GitHub Actions.
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838

## Technology Stack 🚀

<<<<<<< HEAD
- **Frontend**: React 18, Vite 6
- **Backend**: FastAPI, Python 3.9+
- **Database**: Supabase (PostgreSQL) with Row Level Security
- **Authentication**: Supabase Auth
- **AI Integration**: OpenAI, Anthropic, Google Gemini, Ollama
- **Monitoring**: Prometheus, Grafana
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

## Supported AI Providers

| Provider | Models | Streaming |
|----------|--------|-----------|
| OpenAI | GPT-4, GPT-4o Mini, GPT-3.5 Turbo | Yes |
| Anthropic | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku | Yes |
| Google Gemini | Gemini 1.5 Pro, 1.5 Flash, 1.0 Pro | Yes |
| Ollama (Local) | Llama 3, Mistral, Mixtral, Code Llama, Phi-3, Gemma 2 | Yes |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.9+
- Supabase account (free tier works)
- At least one AI provider API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/AstrovoxAi.git
   cd AstrovoxAi
   ```

2. **Install frontend dependencies:**
   ```bash
   npm install
   ```

3. **Install backend dependencies:**
   ```bash
   cd 02-Backend
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. **Set up the database:**
   - Run the SQL in `database/schemas/supabase_setup.sql` in your Supabase SQL editor

### Running Locally

1. **Start the backend:**
   ```bash
   cd 02-Backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend:**
   ```bash
   npm run dev
   ```

3. **Open** http://localhost:5173 in your browser

### Docker Deployment

```bash
docker-compose up --build
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | Yes | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |
| `SUPABASE_URL` | Yes | Supabase project URL (backend) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `GEMINI_API_KEY` | No | Google Gemini API key |
| `OLLAMA_BASE_URL` | No | Ollama server URL (default: http://localhost:11434) |
| `ALLOWED_ORIGINS` | No | Comma-separated allowed CORS origins |
| `RATE_LIMIT` | No | Rate limit (default: 120/minute) |
| `DAILY_AI_LIMIT` | No | Daily AI usage quota per user (default: 50) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |
| `ENVIRONMENT` | No | development, staging, production |

*At least one AI provider key is required.
=======
- **Frontend**: React, Vite
- **Backend**: FastAPI, Python 3.9+
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **AI Integration**: OpenAI API
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

## Getting Started

To set up and run ASTRAVOX Ai locally, please refer to the [SETUP.md](SETUP.md) guide.

For production deployment, see the [DEPLOYMENT.md](DEPLOYMENT.md) guide.
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838

## API Documentation

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Register new user |
| POST | `/auth/login` | Login with email/password |
| POST | `/auth/logout` | Logout |
| POST | `/auth/reset-password` | Send password reset email |
| GET | `/auth/me` | Get current user |
| POST | `/auth/refresh` | Refresh access token |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/conversations` | Create conversation |
| GET | `/chat/conversations` | List conversations |
| GET | `/chat/conversations/{id}` | Get conversation |
| GET | `/chat/conversations/{id}/messages` | Get messages |
| POST | `/chat/message` | Send message (supports streaming) |
| GET | `/chat/models` | List available models |
| POST | `/chat/conversations/{id}/title` | Update title |
| DELETE | `/chat/conversations/{id}` | Delete conversation |

### Memory

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/memory/save` | Save memory entry |
| GET | `/memory/` | Get user memory |
| POST | `/memory/extract-from-conversation` | Extract from conversation |
| POST | `/memory/context` | Get formatted context |
| POST | `/memory/auto-extract` | LLM-powered extraction |

### Embeddings

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/embeddings/` | Generate batch embeddings |
| POST | `/embeddings/one` | Generate single embedding |
| GET | `/embeddings/status` | Service status |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/health/readiness` | Readiness probe |
| GET | `/health/liveness` | Liveness probe |
| GET | `/metrics` | Prometheus metrics |

## Streaming

The chat endpoint supports Server-Sent Events (SSE) streaming:

```json
POST /chat/message
{
  "conversation_id": 1,
  "message": "Hello!",
  "model": "gpt-4",
  "stream": true
}
```

Response (SSE):
```
data: Hello
data: ! How
data: can I
data: help?
data: [DONE]
```

## Project Structure

```
AstrovoxAi/
<<<<<<< HEAD
├── src/                        # React frontend
│   ├── app.jsx                 # Main app component
│   ├── auth.jsx                # Authentication UI
│   ├── Dashboard.jsx           # Main dashboard
│   ├── Chat.jsx                # Chat interface
│   ├── Sidebar.jsx             # Conversation sidebar
│   ├── MemoryPanel.jsx         # Memory management
│   ├── SettingsPanel.jsx       # User settings
│   ├── telemetry.jsx           # System telemetry
│   ├── terminalconsole.jsx     # Terminal console
│   ├── supabase.js             # Supabase client
│   ├── main.jsx                # React entry point
│   └── terminal/               # Terminal engine
├── 02-Backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI app
│   │   ├── auth.py             # Auth routes
│   │   ├── chat.py             # Chat routes (with streaming)
│   │   ├── api.py              # General API routes
│   │   ├── memory.py           # Memory routes
│   │   ├── embeddings.py       # Embedding service
│   │   ├── embeddings_route.py # Embedding API routes
│   │   ├── database.py         # Database operations
│   │   ├── middleware.py        # Security middleware
│   │   ├── security_headers.py # Security headers
│   │   ├── rate_limit.py       # Rate limiting
│   │   ├── logging_config.py   # Logging configuration
│   │   ├── metrics.py          # Prometheus metrics
│   │   ├── telemetry.py        # Telemetry routes
│   │   ├── terminal.py         # Terminal routes
│   │   ├── storage.py          # File storage
│   │   ├── usage.py            # Usage quotas
│   │   └── providers/          # AI provider implementations
│   │       ├── base.py         # Abstract base class
│   │       ├── models.py       # Model registry
│   │       ├── factory.py      # Provider factory
│   │       ├── openai_provider.py
│   │       ├── anthropic_provider.py
│   │       ├── gemini_provider.py
│   │       └── ollama_provider.py
│   ├── tests/                  # Backend tests
│   │   ├── conftest.py
│   │   ├── test_providers.py
│   │   ├── test_embeddings.py
│   │   ├── test_integration.py
│   │   ├── test_health.py
│   │   ├── test_terminal.py
│   │   └── ...
│   └── requirements.txt
├── database/                   # Database schema
├── monitoring/                 # Prometheus/Grafana config
├── .github/workflows/          # CI/CD
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
└── package.json
```

## Testing

```bash
# Backend tests
cd 02-Backend
pytest

# Frontend lint
npm run lint

# Frontend typecheck
npm run typecheck

# Frontend build
npm run build
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS errors | Check `ALLOWED_ORIGINS` includes your frontend URL |
| Provider not working | Verify API key is set in `.env` |
| Ollama not connecting | Ensure Ollama is running: `ollama serve` |
| Database errors | Run the schema SQL in Supabase |
| Rate limit exceeded | Wait or increase `RATE_LIMIT` in `.env` |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   React     │────▶│   FastAPI    │────▶│   Supabase      │
│   Frontend  │◀────│   Backend    │◀────│   (PostgreSQL)  │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────┴───────┐
                    │  AI Providers │
                    │  - OpenAI     │
                    │  - Anthropic  │
                    │  - Gemini     │
                    │  - Ollama     │
                    └──────────────┘
=======
├── src/                    # React frontend components and logic
│   ├── app.jsx            # Main application component
│   ├── auth.jsx           # Authentication component
│   ├── Dashboard.jsx      # Main dashboard
│   ├── Chat.jsx           # Chat interface
│   ├── Sidebar.jsx        # Conversation sidebar
│   ├── MemoryPanel.jsx    # Memory management
│   ├── SettingsPanel.jsx  # User settings
│   ├── telemetry.jsx      # System telemetry
│   ├── terminalconsole.jsx # Terminal console
│   ├── supabase.js        # Supabase client
│   └── main.jsx           # React entry point
├── 02-Backend/            # FastAPI backend application
│   ├── app/
│   │   ├── main.py        # FastAPI app with CORS and rate limiting
│   │   ├── auth.py        # Authentication routes
│   │   ├── chat.py        # Chat routes with rate limiting
│   │   ├── api.py         # API routes
│   │   ├── memory.py      # Memory routes
│   │   ├── database.py    # Database operations
│   │   ├── supabase_client.py # Singleton Supabase client
│   │   └── auth_utils.py  # Shared authentication utilities
│   ├── tests/             # Backend tests
│   └── requirements.txt    # Python dependencies
├── database/               # Database schema and migration scripts
│   ├── schemas/
│   │   └── supabase_setup.sql # Database schema
│   └── migrations/
│       └── 0001_indexes_and_signup_trigger.sql # Performance indexes
├── .github/               # GitHub Actions CI/CD
│   └── workflows/
│       └── ci.yml         # CI/CD pipeline
├── .env.example            # Example environment variables
├── Dockerfile.backend      # Backend Docker configuration
├── Dockerfile.frontend     # Frontend Docker configuration
├── docker-compose.yml      # Docker Compose configuration
├── nginx.conf              # Nginx configuration for frontend
├── package.json            # Frontend dependencies and scripts
├── vite.config.js          # Vite build configuration
├── index.html              # Frontend HTML entry point
├── README.md               # Project overview
├── SETUP.md                # Setup and installation guide
├── DEPLOYMENT.md           # Deployment guide
├── API.md                  # API documentation
└── ROADMAP.md              # Future development roadmap
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838
```

## Contributing

We welcome contributions! Please refer to the [ROADMAP.md](ROADMAP.md) for planned features.

## License

MIT License

## Authors
## Prabesh Paudel

<<<<<<< HEAD
**Prabesh Paudel**  

- ***Founder & Chief Executive Officer (CEO), Chief Technology Officer (CTO), Chief AI Architect, Product Vision Lead, Lead Software Architect, Full-Stack Developer, Backend Engineer, Frontend Engineer, AI Systems Engineer, Distributed Systems Engineer, Platform Engineer, AI Runtime Engineer, AI Compiler Engineer, Workflow Engine Developer, API Engineer, Cloud Infrastructure Engineer, DevOps Engineer, Site Reliability Engineer (SRE), Security Engineer, Identity & Access Management (IAM) Engineer, Performance Engineer, Reliability Engineer, Knowledge Systems Engineer, Memory Systems Engineer, Data Platform Engineer, SDK & Developer Experience Engineer, QA Automation Engineer, Test Infrastructure Engineer, Technical Documentation Lead, Research & Development Engineer, Open Source Maintainer, Lead System Integrator, Principal Software Engineer, Creator of AstrovoxAI.***


**Dipson Baral** - *Co-Founder*

**Ranjit Paudel** - *Member of Astrovox*

---

**Version**: 1.0.0
**Status**: Production-ready
=======
    Founder & Chief Executive Officer (CEO)

    Chief AI Architect

    Principal Software Engineer

    Lead Full-Stack Engineer

    Software Solutions Architect

    AI Systems Designer

    DevOps Engineer

    Product Strategist

    Technical Lead

Dipson Baral

    Co-Founder

    Senior Full-Stack Software Engineer

    Backend Engineer

    DevOps Engineer

    API & Database Engineer

Susanta Baral

    AI Research Engineer

    Machine Learning Engineer

    Data & AI Engineer

    AI Model Integration Engineer

    Prompt Engineering Specialist

## TOTAL TASKS COMPLETED 
Project Architecture       ██████████ 100%

Frontend Migration         ██████████ 100%

Backend Migration          ██████████ 100%

Developer Standards        ██████████ 100%

Documentation              █████████░ 95%

CLI Tools                  ██████████ 100%

Telemetry Backend          ██████████ 100%

Telemetry Frontend         ██████████ 100%

Terminal Console           ██████████ 100%

API Documentation          █████████░ 95%

Production Readiness       █████████░ 95%
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838
