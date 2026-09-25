# Architecture Diagrams

Visual representations of the Astrovox AI system architecture.

For prose architecture details, see [ARCHITECTURE.md](./ARCHITECTURE.md).
For data-flow narratives, see [DATA_FLOW.md](./DATA_FLOW.md).

## System Architecture

```mermaid
graph TB
    subgraph Client
        Web[Next.js Frontend]
    end

    subgraph CDN
        Vercel[Vercel Edge]
    end

    subgraph LoadBalancer
        LB[Render Load Balancer]
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

## Component Diagram

```mermaid
graph LR
    subgraph Core
        Auth[Auth Service]
        Memory[Memory Service]
        RAG[RAG Engine]
        Agents[Agent System]
        Billing[Billing]
    end

    subgraph Infrastructure
        DB[(Database)]
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

## Request Flow

```mermaid
graph LR
    A[User Request] --> B{Authenticated?}
    B -->|No| C[Return 401]
    B -->|Yes| D{Rate Limited?}
    D -->|Yes| E[Return 429]
    D -->|No| F[Load Context]
    F --> G{Stream?}
    G -->|Yes| H[SSE Response]
    G -->|No| I[Wait for Complete]
    I --> J[Return JSON]
    H --> K[Save to DB]
    J --> K
```

## Provider Selection

```mermaid
graph TD
    A[Incoming Request] --> B{Has Preferred Model?}
    B -->|Yes| C[Route to Preferred Provider]
    B -->|No| D{Provider Preference Set?}
    D -->|Yes| E[Route to Preferred Provider]
    D -->|No| F{Model Capability Required?}
    F -->|Yes| G[Route to Best Provider for Task]
    F -->|No| H[Route to Default Provider]
    C --> I[Execute Request]
    E --> I
    G --> I
    H --> I
    I --> J[Return Response]
```

## Caching Strategy

```mermaid
graph LR
    A[Request] --> B{Cache Hit?}
    B -->|Yes| C[Return Cached]
    B -->|No| D[Call Provider]
    D --> E{Response Valid?}
    E -->|Yes| F[Cache Response]
    E -->|No| G[Return Error]
    F --> H[Return Response]
    C --> H
```

## Deployment Architecture

```mermaid
graph TB
    subgraph CloudProvider
        subgraph Vercel
            FE[Frontend]
        end

        subgraph Render
            LB[Load Balancer]
            API[API Instances]
            WS[WebSocket Instances]
            Workers[Worker Instances]
        end

        subgraph Supabase
            PG[(PostgreSQL)]
            Auth[Auth Service]
            Storage[Storage]
        end

        subgraph RedisCloud
            R[(Redis Cache)]
        end
    end

    User --> FE
    FE --> LB
    LB --> API
    LB --> WS
    API --> Workers
    API --> PG
    API --> Auth
    API --> Storage
    API --> R
```

## Monitoring Architecture

```mermaid
graph LR
    A[Application] --> B[Metrics Exporter]
    A --> C[Log Exporter]
    A --> D[Trace Exporter]

    B --> E[Prometheus]
    C --> F[Loki]
    D --> G[Jaeger]

    E --> H[Grafana]
    F --> H
    G --> H

    H --> I[Alerts]
    I --> J[PagerDuty]
    I --> K[Slack]
```

## Security Architecture

```mermaid
graph TB
    A[Incoming Request] --> B[WAF]
    B --> C[Rate Limiter]
    C --> D{Authenticated?}
    D -->|No| E[Auth Endpoints Only]
    D -->|Yes| F[Input Validator]
    F --> G{Valid Input?}
    G -->|No| H[Return 400]
    G -->|Yes| I[Authorize]
    I --> J{Authorized?}
    J -->|No| K[Return 403]
    J -->|Yes| L[Process Request]
    L --> M[Audit Log]
    M --> N[Response]
```

## Directory Structure

```
astrovox/
├── 02-Backend/
│   ├── app/
│   │   ├── api/           # API routers
│   │   ├── core/          # Core configuration
│   │   ├── models/        # Data models
│   │   ├── services/      # Business logic
│   │   ├── providers/     # AI provider integrations
│   │   └── middleware/     # HTTP middleware
│   ├── tests/             # Backend tests
│   └── requirements.txt
├── src/
│   ├── components/        # React components
│   ├── hooks/             # Custom hooks
│   ├── stores/            # State management
│   ├── utils/             # Utilities
│   └── styles/            # Styles
├── docs/                  # Documentation
├── database/              # Database schemas and migrations
├── sdk/                   # Official SDKs
│   ├── python/
│   ├── typescript/
│   ├── go/
│   └── rust/
├── k8s/                   # Kubernetes configs
├── helm/                  # Helm charts
└── charts/                # Monitoring dashboards
```

## Technology Stack

### Frontend
- **Framework**: React 18 + Vite 6
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand + React Query
- **UI Components**: Radix UI
- **Animations**: Framer Motion

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.9+
- **ORM**: SQLAlchemy
- **Validation**: Pydantic
- **Task Queue**: Celery + Redis

### Data
- **Primary DB**: Supabase (PostgreSQL + pgvector)
- **Cache**: Redis
- **Search**: Neo4j (knowledge graph)

### AI/ML
- **Providers**: OpenAI, Anthropic, Gemini, Groq, Ollama
- **Embeddings**: OpenAI, Gemini
- **Vector DB**: pgvector

### Infrastructure
- **Frontend Hosting**: Vercel
- **Backend Hosting**: Render
- **Monitoring**: Prometheus + Grafana
- **Tracing**: Jaeger
- **CI/CD**: GitHub Actions

