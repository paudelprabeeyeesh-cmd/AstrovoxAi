# AstrovoxAI API

Base URL: `https://api.astrovox.ai` (production) or `http://localhost:8000` (local)

## Authentication

Authenticated endpoints require an `Authorization: Bearer <supabase_token>` header.
Admin-only endpoints additionally require the user to have the `admin` role in Supabase `app_metadata.roles`.

All API responses follow this standard format:
```json
{
  "status": "OK",
  "message": "Operation completed successfully",
  "data": {}
}
```

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Service health check |
| GET | `/health/readiness` | No | Kubernetes readiness probe |
| GET | `/health/liveness` | No | Kubernetes liveness probe |
| GET | `/health/detailed` | Admin | Detailed component health |
| GET | `/metrics` | No | Prometheus metrics |
| GET | `/metrics/prometheus` | No | Prometheus exposition format |

### GET /health
Response:
```json
{ "status": "healthy", "service": "astravox-ai-backend", "version": "2.0.0" }
```

### GET /health/readiness
Response:
```json
{ "status": "ready", "checks": { "database": "ok", "redis": "ok", "neo4j": "ok" } }
```

### GET /health/liveness
Response:
```json
{ "status": "alive", "uptime_seconds": 3600 }
```

---

## Auth

Prefix: `/auth`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/signup` | No | Register new user |
| POST | `/auth/login` | No | Login with email/password |
| POST | `/auth/logout` | No | Logout |
| POST | `/auth/reset-password` | No | Request password reset |
| GET | `/auth/me` | Bearer | Get current user profile |
| GET | `/auth/me/roles` | Bearer | Get current user roles |
| POST | `/auth/oauth` | No | Initiate OAuth flow |
| POST | `/auth/refresh` | No | Refresh access token |

### POST /auth/signup
Request:
```json
{ "email": "user@example.com", "password": "secret", "full_name": "Jane Doe" }
```

Response:
```json
{ "status": "OK", "message": "User registered successfully", "user": { "id": "...", "email": "..." } }
```

---

## Chat

Prefix: `/chat`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/chat/conversations` | Bearer | Create conversation |
| GET | `/chat/conversations` | Bearer | List conversations |
| GET | `/chat/conversations/{id}` | Bearer | Get conversation |
| GET | `/chat/conversations/{id}/messages` | Bearer | List messages |
| POST | `/chat/message` | Bearer | Send message (streaming or sync) |
| GET | `/chat/models` | No | List supported models |
| POST | `/chat/conversations/{id}/title` | Bearer | Update title |
| DELETE | `/chat/conversations/{id}` | Bearer | Delete conversation |

### POST /chat/message
Request:
```json
{ "conversation_id": 1, "message": "Hello", "model": "gpt-4", "stream": false }
```

Response:
```json
{ "status": "OK", "user_message": { ... }, "ai_message": { ... }, "tokens_used": 42, "provider": "openai" }
```

---

## Memory

Prefix: `/memory`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/memory/save` | Bearer | Save memory entry |
| GET | `/memory/` | Bearer | List user memories |
| POST | `/memory/extract-from-conversation` | Bearer | Extract memories from conversation |
| POST | `/memory/context` | Bearer | Get formatted memory context |
| POST | `/memory/auto-extract` | Bearer | LLM-based memory extraction |

### POST /memory/save
Request:
```json
{ "content": "User prefers dark mode", "importance": 2 }
```

---

## Storage

Prefix: `/storage`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/storage/{bucket}/upload` | Bearer | Upload file |
| DELETE | `/storage/{bucket}/{path}` | Bearer | Delete file |
| GET | `/storage/{bucket}/{path}/signed-url` | Bearer | Get signed URL |

### POST /storage/{bucket}/upload
Form data: `file` (UploadFile), query/body: `user_id`, `path`

---

## Safety

Prefix: `/safety`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/safety/moderate` | No | Moderate text |
| POST | `/safety/feedback` | No | Submit feedback |
| GET | `/safety/audit` | Admin | Get audit log |

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Something went wrong |
| 503 | Service Unavailable - Maintenance or overload |

### Error Response Format
```json
{
  "status": "error",
  "message": "Detailed error message",
  "code": "VALIDATION_ERROR",
  "details": {}
}
```

---

## Rate Limits

- Standard users: 120 requests/minute
- Premium users: 300 requests/minute
- AI endpoints: 50 requests/day
- Burst limit: 20 requests/second

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Requests per window
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when window resets
- `Retry-After`: Seconds to wait (on 429)

---

## Webhooks

### Stripe Webhooks

Endpoint: `POST /webhooks/stripe`

Supported events:
- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

---

## SDKs

### Python
```python
import httpx

client = httpx.Client(
    base_url="https://api.astrovox.ai",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
```

### JavaScript
```javascript
const client = axios.create({
  baseURL: 'https://api.astrovox.ai',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## Observability

### Metrics Endpoints
- `GET /metrics` - Legacy metrics
- `GET /metrics/prometheus` - Prometheus exposition format
- `GET /health` - Health check
- `GET /health/readiness` - Readiness probe
- `GET /health/liveness` - Liveness probe

### Tracing
Distributed tracing is available via OpenTelemetry. Configure with:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:14268/api/v1/span
```

### Logging
Structured JSON logs are emitted by default. Configure log level via `LOG_LEVEL` environment variable.

