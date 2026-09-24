# Frequently Asked Questions

## General

### What is AstrovoxAI?

AstrovoxAI is a production-grade, open-source AI chat platform supporting multiple LLM providers, retrieval-augmented generation (RAG), agents, and enterprise features like SSO and audit logging.

### Is AstrovoxAI free?

Yes. The core platform is open source. We offer paid hosting tiers for users who want managed infrastructure.

### Which LLM providers are supported?

OpenAI (GPT-4, GPT-4o), Anthropic (Claude 3/4), Google (Gemini), Groq, and local models via Ollama.

### Where is the source code?

https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi

## Setup

### How do I run locally?

See the [Developer Guide](./developer_guide.md). Requires Docker, Python 3.12, and Node.js 20.

### Do I need a GPU?

No. GPU acceleration is optional and only required for local model inference via Ollama.

### Can I use SQLite instead of PostgreSQL?

No. PostgreSQL with pgvector is required for embeddings and production features.

## API

### Where is the API documentation?

Swagger UI is available at `/docs` when running locally. See [Interactive API Docs](./interactive_api_docs.md).

### How do I authenticate?

Use `/auth/login` to get an access token, then include `Authorization: Bearer <token>` in subsequent requests.

### What rate limits apply?

Default: 120 requests/minute per IP. Configurable via `RATE_LIMIT` env var.

### Do you support streaming?

Yes. Use `/chat/stream` for Server-Sent Events (SSE) streaming.

## RAG

### How do I ingest documents?

Use the `/rag/ingest` endpoint or the Python SDK. Supported formats: PDF, TXT, MD.

### What embedding model is used?

text-embedding-3-small by default. Configurable in `app/rag/embeddings.py`.

### How is vector search implemented?

PostgreSQL with pgvector. Similarity search uses cosine distance by default.

## Agents

### What tools are available?

File operations, web search, code execution (sandboxed), database queries, and custom tools via the plugin framework.

### How do I create a custom agent?

Define a new router in `app/routers/` and register it in `app/main.py`. See the plugin framework docs.

### Is code execution safe?

Yes. Code execution runs in a sandboxed subprocess with resource limits and network isolation.

## Deployment

### How do I deploy to production?

See [Deployment Guide](./DEPLOYMENT_GUIDE.md). Supports Docker, Kubernetes, and Helm.

### What cloud providers are supported?

AWS (EKS), GCP (GKE), Azure (AKS), and any Kubernetes cluster. Also supports Fly.io, Render, and Railway.

### How do I set up monitoring?

Prometheus + Grafana + Jaeger are included. See [Monitoring Stack](./MONITORING_STACK.md).

## Billing

### How is usage calculated?

Token usage per user is tracked monthly. See [Capacity Planning](./capacity_planning.md).

### Can I set usage limits?

Yes. Configure `DAILY_AI_LIMIT` per user or use the billing API.

### Do you offer enterprise plans?

Yes. Contact sales for custom SLAs, SSO, and dedicated infrastructure.

## Troubleshooting

### Backend won't start

Check `DATABASE_URL` and `REDIS_URL` are set. Run `docker compose up postgres redis -d`.

### Frontend shows blank page

Check browser console for CORS errors. Verify `ALLOWED_ORIGINS` includes your frontend URL.

### 401 Unauthorized on every request

Token may be expired. Use `/auth/refresh` to get a new access token.

### Rate limited immediately

Behind a proxy? Set `TRUST_PROXY=true` so the rate limiter reads `X-Forwarded-For`.

## Security

### How do I report a vulnerability?

Email security@astrovox.ai or open a private GitHub Security Advisory.

### Are API keys encrypted at rest?

Yes. All secrets are stored in Kubernetes Secrets or a secrets manager. Never commit keys to git.

### Is data encrypted in transit?

Yes. All external traffic uses TLS 1.3. Internal service-to-service traffic uses mTLS in production.

## Community

### How do I contribute?

See [CONTRIBUTING.md](./CONTRIBUTING.md). We welcome PRs, issues, and documentation improvements.

### Where can I ask questions?

- GitHub Discussions
- Discord server (link in README)
- Stack Overflow: tag `astrovoxai`

### Is there a good first issue label?

Yes. Look for `good first issue` in GitHub Issues.
