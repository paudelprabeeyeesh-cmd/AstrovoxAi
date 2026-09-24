# Architecture

## System Overview

AstrovoxAI is a full-stack AI chat platform built with modern cloud-native technologies.

```mermaid
graph TB
    subgraph Client
        Web[Next.js Frontend]
    end
    
    subgraph CDN
        Vercel[Vercel Edge]
    end
    
    subgraph LoadBalancer
        LB[Render / Cloudflare LB]
    end
    
    subgraph Application
        API[FastAPI Backend]
        WS[WebSocket Server]
        Workers[Background Workers]
    end
    
    subgraph Data
        PG[(PostgreSQL/pgvector)]
        R[(Redis)]
        N4[(Neo4j)]
    end
    
    subgraph AI
        Router[LLM Router]
        OpenAI[OpenAI]
        Anthropic[Anthropic]
        Gemini[Gemini]
        Groq[Groq]
        Ollama[Ollama]
    end
    
    subgraph Observability
        Prom[Prometheus]
        Graf[Grafana]
        Jaeg[Jaeger]
    end
    
    Web --> Vercel
    Vercel --> LB
    LB --> API
    LB --> WS
    API --> Workers
    API --> PG
    API --> R
    API --> N4
    API --> Router
    Router --> OpenAI
    Router --> Anthropic
    Router --> Gemini
    Router --> Groq
    Router --> Ollama
    API --> Prom
    Prom --> Graf
    API --> Jaeg
```

## Component Architecture

```mermaid
graph LR
    subgraph Core Services
        Auth[Auth Service]
        Memory[Memory Service]
        RAG[RAG Engine]
        Agents[Agent System]
        Billing[Billing Service]
    end
    
    subgraph Infrastructure
        DB[(PostgreSQL)]
        Cache[(Redis)]
        Queue[(Task Queue)]
    end
    
    subgraph External
        LLM[LLM Providers]
        Stripe[Stripe]
        Email[Email Service]
    end
    
    Auth --> DB
    Auth --> Cache
    Memory --> DB
    Memory --> Cache
    RAG --> DB
    RAG --> Cache
    Agents --> LLM
    Billing --> Stripe
    Auth --> Email
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant R as Router
    participant L as LLM
    participant D as Database
    
    U->>F: Send message
    F->>A: POST /solve
    A->>A: Authenticate
    A->>D: Load context
    A->>R: Select provider
    R->>L: Call LLM
    L-->>R: Stream response
    R-->>A: Yield tokens
    A-->>F: SSE stream
    F-->>U: Display response
```

## Technology Stack

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State:** React Query + Zustand
- **Real-time:** SSE / WebSocket

### Backend
- **Framework:** FastAPI 0.104+
- **Language:** Python 3.12
- **ORM:** Supabase client (PostgreSQL)
- **Queue:** ARQ (async Redis queue)
- **LLM Router:** Custom multi-provider router

### Data
- **Primary DB:** PostgreSQL 16 + pgvector
- **Cache:** Redis 7
- **Graph:** Neo4j (optional)
- **Search:** pgvector + BM25

### Infrastructure
- **Container:** Docker
- **Orchestration:** Kubernetes (EKS)
- **CI/CD:** GitHub Actions
- **Monitoring:** Prometheus + Grafana
- **Tracing:** Jaeger
- **CDN:** Vercel Edge

## Key Design Decisions

### 1. FastAPI over Flask
- Native async support
- Automatic OpenAPI docs
- Pydantic validation
- Better performance for I/O-bound workloads

### 2. PostgreSQL over NoSQL
- Strong consistency for user data
- pgvector for semantic search
- ACID transactions for billing

### 3. Supabase Client over Raw SQL
- Type safety
- Built-in auth integration
- Real-time subscriptions

### 4. Multi-provider LLM Routing
- Avoid vendor lock-in
- Cost optimization
- Fallback on provider failures

### 5. Redis for Caching and Sessions
- Low latency for session data
- Rate limiting backend
- Pub/Sub for WebSocket scaling

## Scaling Strategy

### Horizontal Scaling
- Backend pods scale via HPA (CPU/memory)
- WebSocket connections distributed via Redis Pub/Sub
- Database read replicas for query load

### Caching Strategy
- L1: In-process LRU (hot data)
- L2: Redis (session, rate limit, API responses)
- L3: CDN (static assets)

### Database Scaling
- Read replicas for analytics queries
- Connection pooling via PgBouncer
- Partitioned audit logs by month

## Security Architecture

See [SECURITY_MODEL.md](./SECURITY_MODEL.md) for details.

Key principles:
- Defense in depth
- Least privilege
- Fail secure
- Audit everything

## Observability

### Metrics
- HTTP request rate, latency, errors (RED method)
- Business metrics: DAU, message count, token usage
- Infrastructure: CPU, memory, disk, network

### Tracing
- Distributed traces for every request
- LLM call tracing with prompt/response
- Database query profiling

### Logging
- Structured JSON logs
- Request ID propagation
- Sensitive data redaction

## Future Architecture

### Planned Improvements
- Event sourcing for audit logs
- CQRS for read model optimization
- Service mesh (Istio) for mTLS
- GraphQL gateway for flexible APIs
- Edge functions for low-latency inference
