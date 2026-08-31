# ASTROVOX AI — ARCHITECTURE

## System Overview

AstrovoxAI is a multi-provider AI chat platform with RAG capabilities, autonomous agents, and enterprise-grade security.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │  React App   │  │  Mobile App  │  │  Desktop (Tauri)   │     │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘     │
│         └──────────────────┼──────────────────┘                  │
│                            │ HTTPS                               │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                      API GATEWAY (Nginx)                         │
│  ┌──────────────┐  ┌───────┴───────┐  ┌────────────────┐       │
│  │  Rate Limit  │  │  SSL/TLS      │  │  Load Balance  │       │
│  └──────────────┘  └───────────────┘  └────────────────┘       │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                    FASTAPI APPLICATION                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    MIDDLEWARE STACK                       │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐          │    │
│  │  │ Security   │ │ CORS       │ │ Rate Limit │          │    │
│  │  │ Headers    │ │            │ │            │          │    │
│  │  └────────────┘ └────────────┘ └────────────┘          │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐          │    │
│  │  │ Exception  │ │ Input      │ │ Metrics    │          │    │
│  │  │ Handler    │ │ Validation │ │            │          │    │
│  │  └────────────┘ └────────────┘ └────────────┘          │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    ROUTE HANDLERS                        │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ Auth     │ │ Chat     │ │ Memory   │ │ Agent    │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │Knowledg. │ │Analytics │ │ Monitor  │ │ Security │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    SERVICE LAYER                         │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │    │
│  │  │ Smart Router │ │ Embedding    │ │ AI Agent     │    │    │
│  │  │              │ │ Service      │ │ Manager      │    │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘    │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │    │
│  │  │ Cache        │ │ Session      │ │ Audit        │    │    │
│  │  │ Manager      │ │ Manager      │ │ Logger       │    │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                      DATA & AI LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐      │
│  │  Supabase    │  │  Redis       │  │  AI Providers    │      │
│  │  (PostgreSQL)│  │  (Cache)     │  │  - OpenAI        │      │
│  │  - Auth      │  │  - Sessions  │  │  - Anthropic     │      │
│  │  - Database  │  │  - Results   │  │  - Gemini        │      │
│  │  - Storage   │  │  - Queues    │  │  - Ollama        │      │
│  └──────────────┘  └──────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## Component Diagram

```
                    ┌─────────────────┐
                    │   Frontend      │
                    │   (React/Vite)  │
                    └────────┬────────┘
                             │ HTTP/REST
                    ┌────────▼────────┐
                    │   FastAPI       │
                    │   Application   │
                    └──┬───┬───┬───┬──┘
                       │   │   │   │
          ┌────────────┘   │   │   └────────────┐
          │                │   │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌─────────▼─────────┐
   │  Supabase   │  │  AI Router   │  │  Redis Cache      │
   │  Client     │  │  (4 providers│  │  (Optional)       │
   └─────────────┘  └──────┬──────┘  └──────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼─────┐ ┌────▼─────┐
        │  OpenAI  │ │Anthropic │ │  Gemini  │
        └──────────┘ └──────────┘ └──────────┘
```

## Data Flow

### Chat Request Flow
1. Client sends message to `/chat/message`
2. Middleware: CORS → Security Headers → Rate Limit → Input Validation
3. Chat route validates model and selects provider
4. Smart Router selects optimal provider (with fallback)
5. Provider sends request to AI API
6. Response streamed or returned to client
7. Analytics tracked, memory updated

### RAG Query Flow
1. Document uploaded via `/knowledge/upload`
2. Text chunked into overlapping segments
3. Embeddings generated via Gemini API
4. Vectors stored in memory
5. Query: semantic search via cosine similarity
6. Top-k results returned with source citations

### Agent Task Flow
1. User creates task via `/agent/tasks`
2. Agent generates multi-step plan using LLM
3. Each step executed sequentially
4. Tools invoked as needed (memory, knowledge, calculator)
5. Results aggregated and returned

## Security Architecture

```
Request → WAF → Nginx (SSL) → Rate Limiter → Auth Middleware → Route
                     │              │              │
                     ▼              ▼              ▼
              SSL/TLS        IP Allow/Ban    JWT + RBAC
              Termination    Rate Limiting   Session Mgmt
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 6 |
| Backend | FastAPI, Python 3.10+ |
| Database | Supabase (PostgreSQL) |
| Cache | Redis (optional) |
| AI | OpenAI, Anthropic, Gemini, Ollama |
| Auth | Supabase Auth + JWT |
| Monitoring | Prometheus, Grafana |
| CI/CD | GitHub Actions |
| Deployment | Docker, Fly.io, Railway |
