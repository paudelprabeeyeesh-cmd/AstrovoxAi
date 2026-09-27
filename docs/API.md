# API Documentation

Complete REST API reference for AstrovoxAI. All endpoints return JSON unless otherwise specified.

## Base URLs

```yaml
Development:  http://localhost:8000
Staging:      https://staging-api.astrovox.ai
Production:   https://api.astrovox.ai
```

## Authentication

All authenticated endpoints require a Bearer token:

```http
Authorization: Bearer <jwt_token>
```

Obtain tokens via `/auth/signup` or `/auth/login`. Tokens expire after 1 hour; use `/auth/refresh` to renew.

## Quick Reference

| Domain | Base Path | Auth Required |
|--------|-----------|---------------|
| Health | `/health*` | No |
| Authentication | `/auth/*` | Varies |
| Chat | `/chat/*` | Yes |
| Memory | `/memory/*` | Yes |
| Terminal | `/api/terminal/*` | Yes |
| Embeddings | `/embeddings/*` | Yes |
| Agents | `/api/v1/agents/*` | Yes |
| Workspace | `/api/v1/workspace/*` | Yes |
| Enterprise | `/api/v1/enterprise/*` | Yes |
| RAG | `/api/rag/*` | Yes |
| Billing | `/api/v1/billing/*` | Yes |
| Admin | `/api/v1/admin/*` | Admin |
| Training | `/api/v1/training/*` | Yes |
| Audio | `/api/v1/audio/*` | Yes |
| Monitoring | `/api/v1/monitoring/*` | Yes |
| Safety | `/api/v1/safety/*` | Yes |
| Metrics | `/metrics` | No |

## Health & System

### `GET /healthz`

Basic health check.

**Response 200:**
```json
{"status": "ok"}
```

### `GET /health/live`

Container liveness probe.

**Response 200:**
```json
{"status": "alive"}
```

### `GET /health/ready`

Kubernetes readiness probe.

**Response 200:**
```json
{
  "status": "ready",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "openai": "healthy"
  }
}
```

### `GET /health/detailed`

Detailed health with all services.

**Response 200:**
```json
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "openai": "healthy",
    "anthropic": "healthy",
    "gemini": "healthy"
  },
  "uptime_seconds": 86400
}
```

### `GET /metrics`

Prometheus metrics exposition format.

**Response:** `text/plain`

## Authentication

### `POST /auth/signup`

Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "username": "johndoe"
}
```

**Response 201:**
```json
{
  "status": "OK",
  "message": "User registered successfully",
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

### `POST /auth/login`

Authenticate and receive session tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response 200:**
```json
{
  "status": "OK",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "user",
    "tier": "free"
  },
  "session": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "expires_in": 3600
  }
}
```

### `POST /auth/logout`

Invalidate current session.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{"status": "OK", "message": "Logged out successfully"}
```

### `POST /auth/refresh`

Refresh expired access token.

**Request:**
```json
{"refresh_token": "refresh_token"}
```

### `GET /auth/me`

Get current user profile.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "status": "OK",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "user",
    "tier": "free",
    "avatar_url": "https://..."
  }
}
```

## Chat

### `POST /chat/conversations`

Create a new conversation.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "title": "Project Planning",
  "model": "gpt-4",
  "system_prompt": "You are a helpful assistant."
}
```

**Response 201:**
```json
{
  "status": "OK",
  "conversation": {
    "id": 1,
    "user_id": "uuid",
    "title": "Project Planning",
    "model": "gpt-4",
    "is_archived": false,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### `GET /chat/conversations`

List user's conversations.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max results (1-100) |
| `offset` | int | 0 | Pagination offset |

**Response 200:**
```json
{
  "status": "OK",
  "conversations": [...],
  "count": 10
}
```

### `GET /chat/conversations/{id}/messages`

Get messages for a conversation.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |
| `before_id` | int | — | Fetch before this ID |

### `POST /chat/message`

Send a message. Supports streaming.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "conversation_id": 1,
  "message": "Explain quantum computing",
  "model": "gpt-4",
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 500
}
```

**Response 200 (non-streaming):**
```json
{
  "id": 42,
  "conversation_id": 1,
  "role": "assistant",
  "content": "Quantum computing uses...",
  "model_used": "gpt-4",
  "tokens_used": 150,
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Response (streaming, SSE):**
```
data: Quantum
data:  computing
data:  uses...
data: [DONE]
```

### `POST /chat/conversations/{id}/title`

Update conversation title.

**Request:**
```json
{"title": "New Title"}
```

### `DELETE /chat/conversations/{id}`

Soft-delete a conversation.

**Response 200:**
```json
{"status": "OK", "message": "Conversation deleted"}
```

### `POST /chat/branch`

Branch conversation from a message.

**Request:**
```json
{
  "conversation_id": 1,
  "message_id": 42,
  "title": "Branch title"
}
```

### `GET /chat/models`

List available models.

**Response 200:**
```json
{
  "models": [
    {
      "id": "gpt-4",
      "provider": "openai",
      "display_name": "GPT-4",
      "supports_streaming": true,
      "max_tokens": 8192,
      "description": "Most capable GPT-4 model"
    }
  ]
}
```

## Memory

### `POST /memory/save`

Save a memory entry.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "content": "User prefers TypeScript",
  "importance": 3
}
```

**Response 201:**
```json
{
  "status": "OK",
  "memory": {
    "id": 1,
    "user_id": "uuid",
    "content": "User prefers TypeScript",
    "importance": 3,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### `GET /memory/`

Get user's memory entries.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |

### `POST /memory/extract-from-conversation`

Extract memory from conversation.

**Request:**
```json
{"conversation_id": 1}
```

### `POST /memory/context`

Get formatted memory context.

**Request:**
```json
{"max_tokens": 2000}
```

**Response 200:**
```json
{
  "status": "OK",
  "context": "Relevant memory: User prefers TypeScript..."
}
```

### `DELETE /memory/{id}`

Delete memory entry.

## Embeddings

### `POST /embeddings/`

Generate batch embeddings.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "texts": ["Hello world", "AstrovoxAI is amazing"],
  "model": "text-embedding-004"
}
```

**Response 200:**
```json
{
  "status": "OK",
  "embeddings": [
    {
      "text": "Hello world",
      "embedding": [0.012, -0.034, ...],
      "dimensions": 768
    }
  ]
}
```

## Agents

### `POST /api/v1/agents/{role}/run`

Execute agent task.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "task": "Research the latest AI safety papers",
  "context": {}
}
```

### `POST /api/v1/agents/tools/register`

Register a new tool.

**Request:**
```json
{
  "name": "web_search",
  "description": "Search the web",
  "parameters": [...],
  "func": "search_web"
}
```

## RAG

### `POST /api/rag/index`

Index documents for retrieval.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "documents": [
    {"id": "doc-1", "text": "Document content..."}
  ],
  "collection": "default"
}
```

### `POST /api/rag/search`

Search indexed documents.

**Request:**
```json
{
  "query": "How do I deploy to production?",
  "top_k": 5,
  "collection": "default"
}
```

**Response 200:**
```json
{
  "status": "OK",
  "results": [
    {
      "id": "doc-1",
      "score": 0.92,
      "text": "Document content..."
    }
  ]
}
```

## Training

### `POST /api/v1/training/fine-tune`

Initiate fine-tuning job.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "model": "llama-2-7b",
  "dataset_id": "dataset-123",
  "method": "lora",
  "hyperparameters": {
    "epochs": 3,
    "batch_size": 8,
    "learning_rate": 2e-4,
    "lora_rank": 16
  }
}
```

**Response 202:**
```json
{
  "status": "OK",
  "job_id": "job-123",
  "status": "queued"
}
```

### `GET /api/v1/training/jobs/{id}`

Get training job status.

**Response 200:**
```json
{
  "id": "job-123",
  "status": "running",
  "progress": 0.45,
  "current_epoch": 2,
  "total_epochs": 3,
  "current_loss": 0.32
}
```

## Safety

### `POST /api/v1/safety/moderate`

Moderate content.

**Request:**
```json
{"content": "User-generated content"}
```

**Response 200:**
```json
{
  "flagged": false,
  "categories": {
    "toxicity": 0.01,
    "harassment": 0.00,
    "violence": 0.00
  }
}
```

### `POST /api/v1/safety/pii/detect`

Detect PII.

**Response 200:**
```json
{
  "has_pii": true,
  "entities": [
    {"type": "email", "value": "user@example.com", "start": 0, "end": 16}
  ]
}
```

## Error Codes

| Status | Code | Description |
|--------|------|-------------|
| 400 | `BAD_REQUEST` | Invalid request body or parameters |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication token |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | Dependency unavailable |

**Error Response Format:**
```json
{
  "status": "error",
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests",
  "details": {
    "retry_after": 60
  }
}
```

## Pagination

List endpoints support `limit` and `offset` query parameters.

```json
{
  "status": "OK",
  "data": [...],
  "count": 100,
  "limit": 50,
  "offset": 0
}
```

## Rate Limiting

- Default: 120 requests/minute per IP
- Configurable via `RATE_LIMIT` environment variable
- Exceeded requests return `429 Too Many Requests`
- Response includes `Retry-After` header

## Versioning

The API is versioned via URL path prefix `/api/v1/`. Breaking changes will be released under new versions.
