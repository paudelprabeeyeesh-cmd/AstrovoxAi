# Architecture Overview

AstrovoxAI is a production-ready AI chat platform with multi-provider LLM support, persistent memory, agent systems, RAG, enterprise features, and a complete model training and inference toolkit.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Clients"
        WEB[React Frontend]
        MOBILE[Mobile Apps]
        SDK[SDK Clients]
        CLI[Terminal CLI]
    end

    subgraph "Edge Layer"
        LB[Load Balancer / Nginx]
        TLS[TLS Termination]
        WAF[Rate Limiting + Security]
    end

    subgraph "Application Layer"
        API[FastAPI Backend]
        MW[Middleware Stack]
        ROUTERS[API Routers]
    end

    subgraph "Service Layer"
        PROVIDER[Provider Factory]
        MEMORY[Memory Engine]
        CONTEXT[Context Builder]
        ANALYTICS[Analytics Engine]
    end

    subgraph "Data Layer"
        PG[(Supabase PostgreSQL + RLS)]
        REDIS[(Redis Cache)]
        S3[Object Storage]
    end

    subgraph "AI Providers"
        OPENAI[OpenAI]
        ANTHROPIC[Anthropic]
        GEMINI[Gemini]
        OLLAMA[Ollama Local]
        GROQ[Groq]
    end

    subgraph "Observability"
        PROM[Prometheus]
        GRAF[Grafana]
        LOGS[Structured Logs]
    end

    WEB --> LB
    MOBILE --> LB
    SDK --> LB
    CLI --> LB

    LB --> TLS
    TLS --> WAF
    WAF --> API

    API --> MW
    MW --> ROUTERS
    ROUTERS --> PROVIDER
    ROUTERS --> MEMORY
    ROUTERS --> CONTEXT
    ROUTERS --> ANALYTICS

    PROVIDER --> OPENAI
    PROVIDER --> ANTHROPIC
    PROVIDER --> GEMINI
    PROVIDER --> OLLAMA
    PROVIDER --> GROQ

    MEMORY --> PG
    ANALYTICS --> REDIS
    API --> PG
    API --> REDIS

    API --> PROM
    PROM --> GRAF
    API --> LOGS
```

## System Components

### Frontend Layer

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   App.jsx   │  │   Chat.jsx   │  │   Sidebar.jsx     │  │
│  │  Shell &    │  │  Message UI  │  │  Conversation     │  │
│  │  Routing    │  │  Streaming   │  │  Navigation       │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ MemoryPanel │  │ Terminal     │  │ SettingsPanel     │  │
│  │ Memory UI   │  │ CLI Console  │  │ User Prefs        │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│  State: Zustand | Server: React Query | HTTP: Axios         │
└─────────────────────────────────────────────────────────────┘
```

**Key Technologies:**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | React 18 | UI components |
| Build Tool | Vite 6 | Fast HMR and bundling |
| Language | TypeScript | Type safety |
| Styling | Tailwind CSS | Utility-first CSS |
| Components | Radix UI | Accessible primitives |
| Animation | Framer Motion | Motion library |
| State | Zustand | Global client state |
| Server State | React Query | Caching and mutations |
| Routing | React Router | Navigation |
| Editor | Monaco Editor | Code editing in chat |

### Backend Layer

```mermaid
graph TD
    subgraph "Middleware Stack"
        M1[GlobalException]
        M2[SecurityHeaders]
        M3[IPEnforcement]
        M4[UserAgent]
        M5[RequestLogging]
        M6[Idempotency]
        M7[RequestTimeout]
        M8[PayloadSizeLimit]
        M9[GracefulShutdown]
        M10[ContentNegotiation]
        M11[HTTPSRedirect]
        M12[PIIRedaction]
        M13[StructuredLogging]
    end

    subgraph "API Routers"
        R1[auth]
        R2[chat]
        R3[memory]
        R4[terminal]
        R5[embeddings]
        R6[agents]
        R7[workspace]
        R8[enterprise]
        R9[rag]
        R10[billing]
        R11[admin]
        R12[training]
        R13[audio]
        R14[neural_bci]
        R15[quantum]
        R16[safety]
        R17[analytics]
        R18[observability]
    end

    subgraph "Service Layer"
        S1[ProviderFactory]
        S2[MemoryEngine]
        S3[ContextBuilder]
        S4[AnalyticsEngine]
        S5[MetricsCollector]
        S6[LLMClient]
    end

    M1 --> M2 --> M3 --> M4 --> M5 --> M6 --> M7 --> M8 --> M9 --> M10 --> M11 --> M12 --> M13
    M13 --> R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8 & R9 & R10 & R11 & R12 & R13 & R14 & R15 & R16 & R17 & R18
    R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8 & R9 & R10 & R11 & R12 & R13 & R14 & R15 & R16 & R17 & R18 --> S1 & S2 & S3 & S4 & S5 & S6
```

**Middleware stack (order matters):**

1. `GlobalExceptionMiddleware` — Catches unhandled exceptions
2. `SecurityHeadersMiddleware` — CSP, HSTS, X-Frame-Options
3. `IPEnforcementMiddleware` — IP allowlisting/blocklisting
4. `UserAgentMiddleware` — User-Agent validation
5. `RequestLoggingMiddleware` — Structured logging with correlation IDs
6. `IdempotencyMiddleware` — Prevents duplicate writes
7. `RequestTimeoutMiddleware` — 30s request timeout
8. `PayloadSizeLimitMiddleware` — 10MB payload limit
9. `GracefulShutdownMiddleware` — Drain in-flight requests
10. `ContentNegotiationMiddleware` — JSON/MessagePack negotiation
11. `HTTPSRedirectMiddleware` — Force HTTPS in production
12. `PIIRedactionMiddleware` — Redact sensitive data from logs
13. `StructuredLoggingMiddleware` — JSON-formatted structured logs

### Data Layer

```mermaid
graph LR
    subgraph "Supabase PostgreSQL"
        AUTH[auth.users]
        PROFILES[profiles]
        CONVS[conversations]
        MSGS[messages]
        MEM[ai_memory]
        SETTINGS[user_settings]
    end

    subgraph "Redis"
        CACHE[Cache]
        SESSION[Session Store]
        RATE[Rate Limiter]
    end

    subgraph "Object Storage"
        FILES[File Uploads]
        CKPT[Model Checkpoints]
    end

    AUTH --> PROFILES
    PROFILES --> CONVS
    CONVS --> MSGS
    AUTH --> MEM
    AUTH --> SETTINGS
```

**Database schema:**

```sql
-- Core tables (simplified)
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

### AI Provider Abstraction

```mermaid
graph TD
    subgraph "Provider Interface"
        BASE[BaseProvider ABC]
        BASE --> CHAT[chat]
        BASE --> STREAM[stream]
        BASE --> TOKENS[count_tokens]
    end

    subgraph "Providers"
        P1[OpenAI]
        P2[Anthropic]
        P3[Gemini]
        P4[Ollama]
        P5[Groq]
        P6[SmartRouter]
    end

    BASE --> P1 & P2 & P3 & P4 & P5
    P6 --> P1 & P2 & P3 & P4 & P5

    subgraph "Factory"
        F[ProviderFactory]
        M[ModelRegistry]
    end

    F --> BASE
    M --> F
```

All AI providers implement a common interface:

```python
class BaseProvider(ABC):
    @abstractmethod
    async def chat(self, messages, model, **kwargs) -> str: ...
    @abstractmethod
    async def stream(self, messages, model, **kwargs) -> AsyncGenerator[str, None]: ...
    @abstractmethod
    def count_tokens(self, text) -> int: ...
```

## Deployment Topology

### Development (Docker Compose)

```mermaid
graph TD
    subgraph "docker-compose.yml"
        F[Frontend :5173]
        B[Backend :8000]
        R[Redis :6379]
        P[PostgreSQL via Supabase]
    end

    F --> B
    B --> R
    B --> P
```

### Production (Kubernetes)

```mermaid
graph TD
    subgraph "Kubernetes Cluster"
        ING[Ingress NGINX]
        subgraph "Backend Pods"
            BP1[Pod 1]
            BP2[Pod 2]
            BPN[Pod N]
        end
        RS[Redis Sentinel]
        PG_PRIMARY[(PostgreSQL Primary)]
        PG_REPLICA[(PostgreSQL Replica)]
    end

    ING --> BP1 & BP2 & BPN
    BP1 & BP2 & BPN --> RS
    BP1 & BP2 & BPN --> PG_PRIMARY
    PG_PRIMARY --> PG_REPLICA
```

## Security Architecture

### Authentication Flow

```
┌────────┐     ┌──────────┐     ┌──────────────┐     ┌─────────────┐
│ Client │────►│ Supabase │────►│   Auth       │────►│   JWT       │
│        │     │   Auth   │     │   Service    │     │   Token     │
└────────┘     └──────────┘     └──────────────┘     └─────────────┘
                                                               │
                                                               ▼
                                                    ┌──────────────────┐
                                                    │   Backend        │
                                                    │   Validates JWT  │
                                                    │   on every req   │
                                                    └──────────────────┘
```

### Authorization Model

| Role | Level | Permissions |
|------|-------|-------------|
| `user` | 1 | Own data, chat, memory |
| `developer` | 2 | User + API access, tool creation |
| `admin` | 3 | Full platform access, user management |

### Network Security

- CORS restricted to configured origins
- Security headers: CSP, HSTS, X-Frame-Options
- IP allowlisting/blocklisting support
- Request payload size limits (10MB)
- Request timeouts (30s)
- HTTPS redirect in production
- PII redaction from logs

## Observability

```mermaid
graph TD
    subgraph "Application"
        APP[FastAPI Backend]
    end

    subgraph "Metrics"
        PROM[Prometheus]
        GRAF[Grafana]
    end

    subgraph "Logging"
        LOG[Structured JSON Logs]
    end

    subgraph "Tracing"
        TRACE[Distributed Traces]
    end

    APP -->|/metrics| PROM
    PROM --> GRAF
    APP -->|logs| LOG
    APP -->|spans| TRACE
```

**Health check endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `GET /healthz` | Simple liveness check |
| `GET /health/live` | Container liveness probe |
| `GET /health/ready` | Dependency health check |
| `GET /health/detailed` | Full service status |

## Scalability Considerations

- **Stateless backend** — Scale horizontally behind load balancer
- **Redis caching** — Reduce database load for frequent queries
- **Connection pooling** — PostgreSQL connection limits managed
- **Async I/O** — All I/O operations use async/await
- **Lazy loading** — Optional heavy modules loaded on demand
- **CDN** — Static assets served via CDN in production
- **Database replication** — Read replicas for reporting queries

## Extension Points

- **Custom tools** — Register tools via `app/api/custom_tools.py`
- **Custom providers** — Implement `BaseProvider` interface
- **Webhooks** — Configure event subscriptions
- **Plugins** — Extend via plugin framework
- **SDK generation** — OpenAPI specs auto-generate clients
- **Extensions** — IDE and browser extensions via extension SDK
- **Middleware** — Custom middleware injection points
