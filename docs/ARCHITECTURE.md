# AstrovoxAI — System Architecture

## Design Principles

1. **Stateless backend** — Horizontal scaling via Kubernetes or Docker Swarm
2. **Provider abstraction** — Unified interface for multiple LLM providers
3. **Tenant isolation** — Row Level Security (RLS) in Supabase PostgreSQL
4. **Observability first** — Structured logging, metrics, and tracing on every request
5. **Security by default** — Rate limiting, input validation, CORS, security headers
6. **Graceful degradation** — Fallback providers, circuit breakers, cached responses

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENTS                                   │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────────┐  │
│  │  React Web │  │  Tauri     │  │  Mobile (iOS / Android)      │  │
│  │  Frontend  │  │  Desktop   │  │  SDK / API Clients           │  │
│  └─────┬──────┘  └─────┬──────┘  └──────────┬───────────────────┘  │
└────────┼───────────────┼─────────────────────┼──────────────────────┘
          │               │                     │
          └───────────────┼─────────────────────┘
                          │ HTTPS / WSS
┌────────────────────────┼───────────────────────────────────────────┐
│                  API GATEWAY / INGRESS                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Nginx / Cloud Load Balancer                                 │  │
│  │  - TLS termination                                           │  │
│  │  - Rate limiting                                             │  │
│  │  - Static asset serving                                      │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────────┘
                                │
┌──────────────────────────────┼──────────────────────────────────────┐
│                        FASTAPI BACKEND                              │
│  ┌───────────────────────────┼──────────────────────────────────┐   │
│  │                    MIDDLEWARE STACK                            │   │
│  │  CORS → Security Headers → Rate Limit → Request Logging      │   │
│  │  → Idempotency → Timeout → Payload Limit → Graceful Shutdown │   │
│  └───────────────────────────┬──────────────────────────────────┘   │
│                               │                                     │
│  ┌────────────────────────────┼─────────────────────────────────┐  │
│  │                     API ROUTERS                                │  │
│  │                                                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │   Auth       │  │   Chat       │  │   Memory         │   │  │
│  │  │   Router     │  │   Router     │  │   Router         │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │   Agents     │  │   Workspace  │  │   Enterprise     │   │  │
│  │  │   Router     │  │   Router     │  │   Router         │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │   RAG        │  │   Billing    │  │   Admin          │   │  │
│  │  │   Router     │  │   Router     │  │   Router         │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  │  Plus: Terminal, Embeddings, Audio, Neural, Quantum, ...      │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                               │                                     │
│  ┌────────────────────────────┼─────────────────────────────────┐  │
│  │                     SERVICE LAYER                              │  │
│  │                                                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │   Provider   │  │   Memory     │  │   Context        │   │  │
│  │  │   Factory    │  │   Engine     │  │   Builder        │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │   LLM        │  │   Analytics  │  │   Metrics        │   │  │
│  │  │   Client     │  │   Engine     │  │   Collector      │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                │
           ┌────────────────────┼────────────────────┐
           │                    │                    │
┌─────────┼─────────┐  ┌────────┼─────────┐  ┌──────┼──────────┐
│ SUPABASE │         │  │  REDIS │         │  │  AI  │ PROVIDERS│
│ PostgreSQL│         │  │ Cache  │         │  │      │          │
│ + Auth   │         │  │ Session│         │  │      │ OpenAI   │
│ + RLS    │         │  │ Rate   │         │  │      │ Anthropic│
│          │         │  │ Limit  │         │  │      │ Gemini   │
│          │         │  │        │         │  │      │ Ollama   │
│          │         │  │        │         │  │      │ Groq     │
└──────────┘         │  └───────┘         │  └──────┘          │
                     │                    │                     │
                     └────────────────────┘                     │
                               │                                 │
                    ┌──────────┴──────────┐                     │
                    │  PROMETHEUS + GRAFANA│                     │
                    │  MONITORING STACK    │                     │
                    └─────────────────────┘                     │
```

---

## Frontend Architecture

### Technology Stack

- **React 18** with functional components and hooks
- **Vite 6** for build tooling and HMR
- **TypeScript** strict mode
- **Tailwind CSS** for utility-first styling
- **Radix UI** for accessible primitives
- **Framer Motion** for animations
- **Zustand** for global state
- **React Query** for server state and caching
- **React Router** for navigation

### Key Modules

| Module | Path | Responsibility |
|--------|------|----------------|
| App Shell | `src/app.jsx` | Routing, layout, theme provider |
| Authentication | `src/auth.jsx` | Login, signup, password reset UI |
| Chat | `src/Chat.jsx` | Main conversation interface |
| Sidebar | `src/Sidebar.jsx` | Conversation list and navigation |
| Memory | `src/MemoryPanel.jsx` | Memory management UI |
| Settings | `src/SettingsPanel.jsx` | User preferences |
| Terminal | `src/terminalconsole.jsx` | Interactive terminal console |
| Telemetry | `src/telemetry.jsx` | System diagnostics display |

### Design System

- **Design Tokens**: `src/design/DesignTokens.js`
- **Typography**: `src/design/TypographyScale.jsx`
- **Motion**: `src/design/MotionLibrary.jsx`
- **Iconography**: `src/design/Iconography.jsx`
- **Dark Mode**: `src/design/DarkModeVariants.jsx`
- **Accessibility**: `src/design/AccessibilitySpecs.js`

### State Management

- **Zustand stores** for client state (auth, settings, UI)
- **React Query** for server state (conversations, messages, memory)
- **Supabase Realtime** for live updates

---

## Backend Architecture

### Application Entry Point

`02-Backend/app/main.py` is the FastAPI application entry point. It:
1. Loads environment variables via `python-dotenv`
2. Configures CORS, security headers, rate limiting
3. Registers 50+ API routers
4. Applies middleware stack
5. Registers lifecycle handlers for graceful shutdown

### Middleware Stack (order matters)

1. **GlobalExceptionMiddleware** — Catches unhandled exceptions
2. **SecurityHeadersMiddleware** — CSP, HSTS, X-Frame-Options
3. **IPEnforcementMiddleware** — IP allowlisting/blocklisting
4. **UserAgentMiddleware** — User-Agent validation
5. **RequestLoggingMiddleware** — Structured request logging with correlation IDs
6. **IdempotencyMiddleware** — Prevents duplicate writes
7. **RequestTimeoutMiddleware** — 30s request timeout
8. **PayloadSizeLimitMiddleware** — 10MB payload limit
9. **GracefulShutdownMiddleware** — Drain in-flight requests
10. **ContentNegotiationMiddleware** — JSON/MessagePack negotiation
11. **HTTPSRedirectMiddleware** — Force HTTPS in production
12. **PIIRedactionMiddleware** — Redact sensitive data from logs
13. **StructuredLoggingMiddleware** — JSON-formatted structured logs

### AI Provider Abstraction

All AI providers implement a common interface defined in `app/providers/base.py`:

```python
class BaseProvider(ABC):
    @abstractmethod
    async def chat(self, messages, model, **kwargs) -> str: ...
    @abstractmethod
    async def stream(self, messages, model, **kwargs) -> AsyncGenerator[str, None]: ...
    @abstractmethod
    def count_tokens(self, text) -> int: ...
```

Registered providers:

| Provider | Module | Models |
|----------|--------|--------|
| OpenAI | `providers/openai_provider.py` | GPT-4, GPT-4o Mini, GPT-3.5 Turbo |
| Anthropic | `providers/anthropic_provider.py` | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku |
| Gemini | `providers/gemini_provider.py` | Gemini 1.5 Pro, 1.5 Flash, 1.0 Pro |
| Ollama | `providers/ollama_provider.py` | Llama 3, Mistral, Mixtral, Phi-3, Gemma 2 |
| Smart Router | `providers/smart_router.py` | Automatic provider selection with fallback |

Provider factory (`providers/factory.py`) resolves providers by model name. Model registry (`providers/models.py`) maps model IDs to provider metadata.

---

## Database Design

### Core Schema

```
auth.users (Supabase managed)
    │
    ├── profiles
    │     ├── id (FK → auth.users)
    │     ├── username, full_name, avatar_url
    │     ├── role, tier
    │     └── metadata (JSONB)
    │
    ├── conversations
    │     ├── id, user_id (FK)
    │     ├── title, summary, model
    │     ├── metadata (JSONB)
    │     ├── is_archived, is_deleted
    │     └── timestamps
    │
    ├── messages
    │     ├── id, conversation_id (FK)
    │     ├── user_id (FK)
    │     ├── role (user/assistant/system/tool)
    │     ├── content, model_used, tokens_used
    │     └── metadata (JSONB)
    │
    ├── ai_memory
    │     ├── id, user_id (FK)
    │     ├── content, importance (1-5)
    │     ├── metadata (JSONB)
    │     └── timestamps
    │
    └── user_settings
          ├── user_id (FK, PK)
          ├── theme, ai_preferences (JSONB)
          ├── notifications_enabled
          └── updated_at
```

### Row Level Security (RLS)

All user-scoped tables enforce RLS:
- Users can only read/write their own data
- Policies use `auth.uid()` for ownership checks
- No cross-tenant data leakage possible

### Migrations

Schema migrations are versioned in `database/migrations/`. The initial schema is in `database/schemas/supabase_setup.sql`.

---

## Data Flow

### Chat Request Flow

```
1. Client sends POST /chat/message
2. CORS + Security Headers middleware
3. Rate limiter checks IP + user quota
4. Auth middleware extracts user_id from JWT
5. Chat router validates conversation ownership
6. Usage tracker checks daily AI limit
7. Context builder loads conversation history + memory
8. Provider factory selects adapter for requested model
9. LLM provider streams response (SSE)
10. Messages are persisted to PostgreSQL
11. Metrics recorded (Prometheus + Analytics)
12. Response streamed to client
```

### Memory Extraction Flow

```
1. User triggers memory extraction
2. Backend fetches recent messages
3. LLM extracts key facts with importance scoring
4. Entries saved to ai_memory table
5. Vector embeddings generated (optional, for RAG)
6. Memory context injected into future prompts
```

---

## Security Architecture

### Authentication
- Supabase Auth (JWT + refresh tokens)
- Token validation on every request
- Session management with automatic refresh

### Authorization
- Role-based access: `user` < `developer` < `admin`
- Resource ownership enforced at database level (RLS)
- API-level permission checks for admin endpoints

### Network Security
- CORS restricted to configured origins
- Security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- IP allowlisting/blocklisting support
- Request payload size limits (10MB)
- Request timeouts (30s)
- HTTPS redirect in production
- PII redaction from logs

### Rate Limiting
- Per-IP: 120 requests/minute (configurable)
- Per-user: Daily AI quota (configurable)
- Endpoint-specific limits for expensive operations

### Data Protection
- Secrets stored in environment variables or Docker secrets
- Service role key never exposed to frontend
- Database connections via connection pooling
- Audit logging for all mutations

---

## Observability

### Structured Logging
- JSON-formatted logs with correlation IDs
- Request/response logging via middleware
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- PII redaction from logs

### Metrics
- Prometheus exposition format at `/metrics`
- Tracked: request count, latency, status codes, AI usage
- Custom metrics for business events

### Health Checks
- `/health/live` — Container health
- `/health/ready` — Dependency health (DB, Redis, providers)
- `/healthz` — Simple OK response

### Dashboards
- Grafana dashboards defined in `monitoring/`
- Key metrics: request rate, error rate, latency, AI usage, active users

---

## Deployment Topology

### Development (Docker Compose)

```
┌─────────────────────────────────────┐
│         docker-compose.yml          │
│                                     │
│  ┌──────────┐  ┌──────────────┐    │
│  │ Frontend │  │   Backend    │    │
│  │ (Vite)   │  │  (Uvicorn)   │    │
│  └──────────┘  └──────┬───────┘    │
│                       │            │
│              ┌────────┴───────┐    │
│              │     Redis      │    │
│              └────────┬───────┘    │
│                       │            │
│              ┌────────┴───────┐    │
│              │   PostgreSQL   │    │
│              │  (via Supabase)│    │
│              └────────────────┘    │
└─────────────────────────────────────┘
```

### Production (Kubernetes)

```
┌───────────────────────────────────────────────────┐
│                   Ingress NGINX                    │
│                 (TLS termination)                  │
└───────────────────────┬───────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────┴────┐     ┌────┴────┐    ┌────┴────┐
    │ Backend │     │ Backend │    │ Backend │
    │  Pod 1  │     │  Pod 2  │    │  Pod N  │
    └────┬────┘     └────┬────┘    └────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
               ┌─────────┴─────────┐
               │    Redis Sentinel │
               └─────────┬─────────┘
                         │
               ┌─────────┴─────────┐
               │  PostgreSQL       │
               │  (Primary + Replica)
               └───────────────────┘
```

Helm charts: `helm/`
Kubernetes manifests: `k8s/`

---

## Module Reference

### Backend Modules

| Module | Path | Purpose |
|--------|------|---------|
| Chat | `app/chat.py` | Conversation CRUD, message streaming |
| Memory | `app/memory.py` | Memory CRUD, context extraction |
| Terminal | `app/terminal.py` | Terminal console API |
| Embeddings | `app/embeddings_route.py` | Text vectorization |
| Providers | `app/providers/` | LLM provider adapters |
| Auth | `app/services/auth/` | Supabase authentication |
| Agents | `app/api/routers/agent_route.py` | Agent lifecycle and execution |
| RAG | `app/routers/rag.py` | Document indexing and retrieval |
| Workspace | `app/api/routers/workspace_route.py` | Team workspaces, folders |
| Enterprise | `app/enterprise/` | SSO, RBAC, billing, teams |
| Billing | `app/billing/` | Subscriptions, invoices, coupons |
| Kernel | `app/kernel/` | Core AI orchestration kernel |
| AIOS | `app/aios/` | AI Operating System runtime |
| AGI Reasoning | `app/agi_reasoning/` | Advanced reasoning modules |
| Analytics | `app/analytics/` | Usage analytics and reporting |
| Observability | `app/observability/` | Monitoring endpoints |
| Safety | `app/safety_routes.py` | Safety and moderation |
| Training | `app/training/` | Fine-tuning and RLHF |
| Audio | `app/routers/audio.py` | Speech-to-text and TTS |
| Neural BCI | `app/routers/neural_bci.py` | Brain-computer interface |
| Quantum | `app/quantum/` | Quantum computing simulation |

### Frontend Modules

| Module | Path | Purpose |
|--------|------|---------|
| Chat UI | `src/components/chat/` | Message rendering, streaming, markdown |
| Workspace | `src/components/workspace/` | Folders, tabs, branching |
| Neural | `src/components/neural/` | BCI, neurofeedback, thought-to-text |
| Quantum | `src/components/quantum/` | Quantum visualization, holographic UI |
| Platform | `src/platform/` | PWA, offline sync, push notifications |
| Hooks | `src/hooks/` | Custom React hooks |
| Services | `src/services/` | API clients, monitoring, sandbox |
| Terminal | `src/terminal/` | Terminal engine and API client |

---

## Scalability Considerations

- **Stateless backend** — Scale horizontally behind load balancer
- **Redis caching** — Reduce database load for frequent queries
- **Connection pooling** — PostgreSQL connection limits managed
- **Async I/O** — All I/O operations use async/await
- **Lazy loading** — Optional heavy modules loaded on demand
- **CDN** — Static assets served via CDN in production
- **Database replication** — Read replicas for reporting queries

---

## Extension Points

- **Custom tools** — Register tools via `app/api/custom_tools.py`
- **Custom providers** — Implement `BaseProvider` interface
- **Webhooks** — Configure event subscriptions
- **Plugins** — Extend via plugin framework (`app/api/routers/plugin_framework.py`)
- **SDK generation** — OpenAPI specs auto-generate clients
- **Extensions** — IDE and browser extensions via extension SDK
- **Middleware** — Custom middleware injection points
