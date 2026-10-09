# Release Notes

## v2.1.0 — 2026-09-24

### Added
- Multi-agent orchestration with shared memory
- Plugin marketplace with sandboxed execution
- Advanced RAG with hybrid search (BM25 + vector)
- WebSocket reconnection with exponential backoff
- Rate limiting on all public endpoints
- Structured JSON logging with request IDs
- Distributed tracing with Jaeger
- Prometheus metrics middleware
- Health checks for LLM providers
- Feature flags via environment variables

### Changed
- `main.py` split into modular routers (32 routers)
- PostgreSQL enforced (SQLite fallback removed)
- Connection pooling via asyncpg
- Token storage migrated to Redis + PostgreSQL

### Fixed
- Gemini adapter migrated to `google.genai`
- Circular imports resolved in `shared_state.py`
- Hardcoded secrets removed from all source files
- SQL injection patterns parameterized
- DuplicateTimeseries bug fixed

### Security
- CSRF protection added
- WebSocket JWT auth enforced
- Email verification required before login
- Password reset tokens invalidated after use
- Brute-force lockout: 5 failures / 15 min

### Infrastructure
- CI/CD pipeline with lint, typecheck, security, test, build, deploy
- Staging environment with Docker + K8s manifests
- Load testing suite (Locust, pytest-benchmark, k6)
- Automated daily backups to S3/R2

## v2.0.0 — 2026-09-10

### Added
- FastAPI backend with 32 routers
- Next.js frontend with Vite
- PostgreSQL + pgvector for embeddings
- Redis for caching, sessions, rate limiting
- Multi-provider LLM routing (OpenAI, Anthropic, Gemini, Groq, Ollama)
- RAG engine with knowledge graph
- Agent framework with tool calling
- Billing integration with Stripe
- SOC 2 audit logging
- Compliance module (GDPR/CCPA)

### Infrastructure
- Docker Compose for local development
- Kubernetes manifests for production
- Helm chart for easy deployment
- GitHub Actions CI/CD
- Prometheus + Grafana monitoring
- Jaeger distributed tracing

## v1.0.0 — 2026-08-15

### Added
- Initial prototype release
- Basic chat functionality
- OpenAI integration
- PostgreSQL database
- Simple authentication
- Docker deployment
