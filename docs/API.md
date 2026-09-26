# AstrovoxAI — REST API Reference

## Base URLs

```
Development:  http://localhost:8000
Production:   https://api.astrovox.ai
```

## Authentication

All authenticated endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

Tokens are obtained via `/auth/login` or `/auth/signup`. Supabase Auth is used for identity management.

---

## Table of Contents

1. [Health & System](#health--system)
2. [Authentication](#authentication)
3. [Chat](#chat)
4. [Memory](#memory)
5. [Terminal](#terminal)
6. [Embeddings](#embeddings)
7. [Agents](#agents)
8. [Workspace](#workspace)
9. [Enterprise](#enterprise)
10. [RAG](#rag)
11. [Billing & Usage](#billing--usage)
12. [Admin](#admin)
13. [Monitoring & Metrics](#monitoring--metrics)

---

## Health & System

### `GET /healthz`
Basic health check.

**Response:**
```json
{
  "status": "ok"
}
```

### `GET /health/liveness`
Kubernetes liveness probe.

**Response:**
```json
{
  "status": "alive"
}
```

### `GET /health/readiness`
Kubernetes readiness probe with dependency checks.

**Response:**
```json
{
  "status": "ready",
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

### `GET /metrics`
Prometheus metrics endpoint.

**Response:** `text/plain` Prometheus exposition format.

---

## Authentication

### `POST /auth/signup`
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response (201):**
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

**Response (200):**
```json
{
  "status": "OK",
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  },
  "session": {
    "access_token": "jwt",
    "refresh_token": "jwt",
    "expires_in": 3600
  }
}
```

### `POST /auth/logout`
Invalidate the current session.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "status": "OK",
  "message": "Logged out successfully"
}
```

### `POST /auth/reset-password`
Send a password reset email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "status": "OK",
  "message": "Password reset email sent"
}
```

### `GET /auth/me`
Get the current authenticated user profile.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "status": "OK",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "avatar_url": "https://...",
    "role": "user",
    "tier": "free"
  }
}
```

### `POST /auth/refresh`
Refresh an expired access token.

**Request:**
```json
{
  "refresh_token": "jwt"
}
```

---

## Chat

### `POST /chat/conversations`
Create a new conversation.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "title": "Project Planning",
  "model": "gpt-4"
}
```

**Response (201):**
```json
{
  "status": "OK",
  "conversation": {
    "id": 1,
    "user_id": "uuid",
    "title": "Project Planning",
    "model": "gpt-4",
    "is_archived": false,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### `GET /chat/conversations`
List the current user's conversations.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Max results (1-100) |
| `offset` | integer | 0 | Pagination offset |

**Response (200):**
```json
{
  "status": "OK",
  "conversations": [...],
  "count": 10
}
```

### `GET /chat/conversations/{id}`
Get conversation details.

**Headers:** `Authorization: Bearer <token>`

### `GET /chat/conversations/{id}/messages`
Get messages for a conversation.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Max results |
| `offset` | integer | 0 | Pagination offset |
| `before_id` | integer | — | Fetch messages before this ID |

### `POST /chat/message`
Send a message to a conversation. Supports streaming.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "conversation_id": 1,
  "message": "Explain quantum computing",
  "model": "gpt-4",
  "stream": true
}
```

**Response (200, non-streaming):**
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

### `GET /chat/models`
List all available AI models.

**Response (200):**
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

### `POST /chat/conversations/{id}/title`
Update conversation title.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "title": "New Title"
}
```

### `DELETE /chat/conversations/{id}`
Soft-delete a conversation.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "status": "OK",
  "message": "Conversation deleted"
}
```

---

## Memory

### `POST /memory/save`
Save a memory entry.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "content": "User prefers TypeScript over JavaScript",
  "importance": 3
}
```

**Response (201):**
```json
{
  "status": "OK",
  "memory": {
    "id": 1,
    "user_id": "uuid",
    "content": "User prefers TypeScript over JavaScript",
    "importance": 3,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### `GET /memory/`
Get the current user's memory entries.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Max results |

**Response (200):**
```json
{
  "status": "OK",
  "memory": [...],
  "count": 25
}
```

### `POST /memory/extract-from-conversation`
Extract important information from a conversation and save as memory.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "conversation_id": 1
}
```

### `POST /memory/context`
Get formatted memory context for injection into prompts.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "max_tokens": 2000
}
```

**Response (200):**
```json
{
  "status": "OK",
  "context": "Relevant memory: ..."
}
```

### `POST /memory/auto-extract`
LLM-powered memory extraction from conversation.

**Headers:** `Authorization: Bearer <token>`

---

## Terminal

### `POST /api/terminal/inject`
Persist a memory entry via the terminal console.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "content": "Important fact to remember"
}
```

**Response (201):**
```json
{
  "status": "OK",
  "memory": {
    "id": 1,
    "content": "Important fact to remember",
    "importance": 1,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### `POST /api/terminal/purge`
Delete all memory entries for the current user. **Destructive operation.**

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "status": "OK",
  "deleted": 42
}
```

### `GET /api/terminal/usage`
Get today's AI usage count and configured daily limit.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "status": "OK",
  "used": 12,
  "limit": 50,
  "remaining": 38,
  "reset_at": "2024-01-02T00:00:00Z"
}
```

---

## Embeddings

### `POST /embeddings/`
Generate batch embeddings for multiple texts.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "texts": ["Hello world", "AstrovoxAI is amazing"],
  "model": "text-embedding-004"
}
```

**Response (200):**
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

### `POST /embeddings/one`
Generate a single embedding.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "text": "Hello world",
  "model": "text-embedding-004"
}
```

### `GET /embeddings/status`
Check embeddings service status.

**Response (200):**
```json
{
  "status": "OK",
  "service": "healthy",
  "provider": "gemini"
}
```

---

## Agents

### `GET /api/v1/agents`
List all registered agents.

**Headers:** `Authorization: Bearer <token>`

### `GET /api/v1/agents/{role}`
Get agent details by role.

**Headers:** `Authorization: Bearer <token>`

### `GET /api/v1/agents/{role}/health`
Get agent health status.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "role": "researcher",
  "status": "healthy",
  "last_active": "2024-01-01T00:00:00Z",
  "tasks_completed": 142
}
```

### `POST /api/v1/agents/{role}/run`
Execute an agent task.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "task": "Research the latest AI safety papers",
  "context": {}
}
```

---

## Workspace

### `GET /api/v1/workspace`
Get current workspace details.

**Headers:** `Authorization: Bearer <token>`

### `POST /api/v1/workspace/folders`
Create a folder.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "name": "Research",
  "parent_id": null
}
```

### `POST /api/v1/workspace/conversations/{id}/share`
Share a conversation with team members.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "user_ids": ["uuid-1", "uuid-2"],
  "permission": "read"
}
```

---

## Enterprise

### `POST /api/v1/enterprise/sso/saml`
SAML SSO authentication.

### `GET /api/v1/enterprise/team/members`
List team members.

**Headers:** `Authorization: Bearer <token>`

### `POST /api/v1/enterprise/billing/subscribe`
Create a subscription.

**Headers:** `Authorization: Bearer <token>`

---

## RAG

### `POST /api/rag/index`
Index documents for retrieval.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "documents": [
    {"id": "doc-1", "text": "Document content here..."}
  ],
  "collection": "default"
}
```

### `POST /api/rag/search`
Search indexed documents.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "query": "How do I deploy to production?",
  "top_k": 5,
  "collection": "default"
}
```

**Response (200):**
```json
{
  "status": "OK",
  "results": [
    {
      "id": "doc-1",
      "score": 0.92,
      "text": "Document content here..."
    }
  ]
}
```

---

## Billing & Usage

### `GET /api/v1/billing/usage`
Get current billing period usage.

**Headers:** `Authorization: Bearer <token>`

### `GET /api/v1/billing/invoices`
List invoices.

**Headers:** `Authorization: Bearer <token>`

### `POST /api/v1/billing/coupons/apply`
Apply a coupon code.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "code": "SUMMER2024"
}
```

---

## Admin

### `GET /api/v1/admin/users`
List all users (admin only).

**Headers:** `Authorization: Bearer <token>`

### `GET /api/v1/admin/metrics`
Platform-wide metrics.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "total_users": 1250,
  "active_today": 340,
  "total_conversations": 8900,
  "total_messages": 45600,
  "ai_requests_today": 12000
}
```

### `POST /api/v1/admin/feature-flags`
Create a feature flag.

**Headers:** `Authorization: Bearer <token>`

---

## Monitoring & Metrics

### `GET /api/v1/monitoring/health`
Detailed health check with all services.

### `GET /api/v1/monitoring/metrics`
Application metrics.

**Response (200):**
```json
{
  "requests_total": 125000,
  "requests_per_second": 45.2,
  "average_latency_ms": 120,
  "error_rate": 0.02,
  "active_connections": 230
}
```

### `GET /api/v1/observability/alerts`
Active alerts.

---

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

### Error Response Format

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

## Rate Limiting

- Default: 120 requests/minute per IP
- Configurable via `RATE_LIMIT` environment variable
- Exceeded requests return `429 Too Many Requests`
- Response includes `Retry-After` header

## Pagination

List endpoints support pagination via `limit` and `offset` query parameters.

Response envelope:
```json
{
  "status": "OK",
  "data": [...],
  "count": 100,
  "limit": 50,
  "offset": 0
}
```

## Versioning

The API is versioned via URL path prefix `/api/v1/`. Breaking changes will be released under new versions.

Policy: [api_versioning_policy.md](api_versioning_policy.md)

## SDKs

Auto-generated SDKs are available:
- Python: `sdk/python/`
- TypeScript: `sdk/typescript/`
- Go: `sdk/go/`
- Rust: `sdk/rust/`

Generate with:
```bash
npm run sdk:generate
```

## Webhooks

See [WEBHOOKS.md](WEBHOOKS.md) for webhook configuration and event types.
