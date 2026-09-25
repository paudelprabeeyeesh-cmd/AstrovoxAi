# Version Compatibility Matrix

## Backend

| Component | Version | Min Python | Notes |
|-----------|---------|------------|-------|
| FastAPI | 0.115.0 | 3.12 | |
| Uvicorn | 0.32.0 | 3.12 | |
| PostgreSQL | 16 | - | pgvector required |
| Redis | 7 | - | |
| Neo4j | 5.23 | - | APOC plugin required |
| Alembic | 1.13+ | 3.12 | Migrations versioned |

## Frontend

| Component | Version | Notes |
|-----------|---------|-------|
| Next.js | 16 | App Router |
| React | 19 | |
| TypeScript | 5.x | Strict mode |
| Tailwind | 3.x | |

## LLM Providers

| Provider | Min API Version | Notes |
|----------|-----------------|-------|
| OpenAI | 2024-01+ | gpt-4o, gpt-4o-mini |
| Anthropic | 2023-06+ | claude-3-5-sonnet |
| Google | v1 | gemini-1.5-pro |
| Groq | v1 | llama-3.3-70b |
| Ollama | 0.1+ | Local models |
| HuggingFace | v1 | Inference API |

## Breaking Changes
- Python 3.11 → 3.12: dataclass changes
- Next.js 15 → 16: cache API changes
- PostgreSQL 15 → 16: minor SQL changes
