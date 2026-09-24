# API Reference

Base URL: `http://localhost:8000`

## Authentication

Authenticated endpoints require an `Authorization: Bearer <supabase_token>` header.
Admin-only endpoints additionally require the user to have the `admin` role in Supabase `app_metadata.roles`.

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Service health check |
| GET | `/health/readiness` | No | Kubernetes readiness probe |
| GET | `/health/liveness` | No | Kubernetes liveness probe |
| GET | `/metrics` | No | Prometheus metrics |

### GET /health
Response:
```json
{ "status": "healthy", "service": "astravox-ai-backend", "version": "2.0.0" }
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
{ "status": "OK", "message": "User registered successfully...", "user": { "id": "...", "email": "..." } }
```

### POST /auth/login
Request:
```json
{ "email": "user@example.com", "password": "secret" }
```
Response:
```json
{ "status": "OK", "message": "Login successful", "user": { "id": "...", "email": "..." }, "session": { "access_token": "...", "refresh_token": "..." } }
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

### POST /chat/conversations
Request:
```json
{ "title": "My chat", "model": "gpt-4" }
```
Response:
```json
{ "status": "OK", "conversation": { "id": 1, "title": "My chat", "model": "gpt-4", ... } }
```

### POST /chat/message
Request:
```json
{ "conversation_id": 1, "message": "Hello", "model": "gpt-4", "stream": false }
```
Response:
```json
{ "status": "OK", "user_message": { ... }, "ai_message": { ... }, "tokens_used": 42, "provider": "openai" }
```

Streaming (`"stream": true`) returns `text/event-stream` with `data: <chunk>` chunks and `data: [DONE]`.

---

## Memory

Prefix: `/memory` (from `app/memory.py`)

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
Response:
```json
{ "status": "OK", "memory": { "id": 1, "user_id": "...", "content": "...", "importance": 2, "created_at": "..." } }
```

### GET /memory/
Query params: `limit` (default 50)
Response:
```json
{ "status": "OK", "memory": [ ... ], "count": 10 }
```

---

## Memory Controls

Prefix: `/memory` (from `app/routers/memory_controls.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/memory/add` | No | Add memory (semantic/episodic/context) |
| POST | `/memory/search` | No | Search memories |
| GET | `/memory/summary/{user_id}` | No | Memory summary |

### POST /memory/add
Request:
```json
{ "user_id": "123", "content": "Prefers Spanish", "memory_type": "semantic", "metadata": {} }
```
Response:
```json
{ "status": "OK", "memory_type": "semantic" }
```

---

## Storage

Prefix: `/storage`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/storage/{bucket}/upload` | No | Upload file |
| DELETE | `/storage/{bucket}/{path}` | No | Delete file |
| GET | `/storage/{bucket}/{path}/signed-url` | No | Get signed URL |

### POST /storage/{bucket}/upload
Form data: `file` (UploadFile), query/body: `user_id`, `path`
Response:
```json
{ "status": "OK", "bucket": "docs", "path": "user/123/file.pdf", "content_type": "application/pdf", "size": 1024 }
```

---

## Telemetry

Prefix: `/telemetry`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/telemetry/event` | Bearer | Track custom event |
| POST | `/telemetry/page-view` | Bearer | Track page view |
| POST | `/telemetry/error` | Bearer | Track error |
| POST | `/telemetry/user-action` | Bearer | Track user action |
| GET | `/telemetry/stats` | Bearer | Get telemetry stats |

### POST /telemetry/event
Request:
```json
{ "event_name": "button_click", "category": "ui", "metadata": { "button": "submit" } }
```
Response:
```json
{ "status": "OK", "event_id": "...", "message": "Event tracked successfully" }
```

---

## Terminal

Prefix: `/api/terminal`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/terminal/inject` | Bearer | Inject memory entry |
| POST | `/api/terminal/purge` | Bearer | Purge all user memory |
| GET | `/api/terminal/usage` | Bearer | Get daily usage |

### POST /api/terminal/inject
Request:
```json
{ "content": "Remember this fact" }
```
Response:
```json
{ "status": "OK", "memory": { ... } }
```

---

## Embeddings

Prefix: `/embeddings`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/embeddings/` | No | Generate embeddings for texts |
| POST | `/embeddings/one` | No | Generate single embedding |
| GET | `/embeddings/status` | No | Check service status |

### POST /embeddings/
Request:
```json
{ "texts": ["hello world"], "model": "text-embedding-3-small" }
```
Response:
```json
{ "embeddings": [[0.1, 0.2, ...]], "model": "text-embedding-3-small", "count": 1 }
```

---

## Models

Prefix: `/models`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/models/register` | No | Register model endpoint |
| POST | `/models/orchestrate` | No | Orchestrate request |
| GET | `/models/stats` | No | Get model stats |
| POST | `/models/fallback-chain` | No | Set fallback chain |

### POST /models/orchestrate
Request:
```json
{ "request_id": "req-1", "capabilities": ["chat"], "max_context": 4096, "timeout_ms": 30000 }
```
Response:
```json
{ "request_id": "req-1", "provider": "openai", "model": "gpt-4", "latency_ms": 1200, "tokens_used": 50, "success": true, "fallback_used": false }
```

---

## Safety

Prefix: `/safety`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/safety/moderate` | No | Moderate text |
| POST | `/safety/feedback` | No | Submit feedback |
| GET | `/safety/audit` | No | Get audit log |

### POST /safety/moderate
Request:
```json
{ "text": "Some content", "user_id": "123", "interaction_id": "int-1" }
```
Response:
```json
{ "safe": true, "flags": [], "confidence": 0.99, "action": "allow" }
```

---

## Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/secrets/rotation-check` | Admin | Check secret rotation status |
| GET | `/audit/log` | Admin | Read audit log |

### GET /audit/log
Query params: `limit` (default 100), `offset` (default 0)
Response:
```json
[ { "id": "...", "timestamp": "...", "event_type": "auth", "actor": "...", "action": "...", "target": "", "details": {}, "status": "success" } ]
```

---

## Example curl Commands

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret"}'

# Create conversation
curl -X POST http://localhost:8000/chat/conversations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"My chat"}'

# Send message
curl -X POST "http://localhost:8000/chat/message?stream=false" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":1,"message":"Hello"}'

# Save memory
curl -X POST http://localhost:8000/memory/save \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content":"Prefers dark mode","importance":2}'

# List memories
curl http://localhost:8000/memory/ \
  -H "Authorization: Bearer <token>"

# Upload file
curl -X POST "http://localhost:8000/storage/docs/upload?user_id=123&path=file.pdf" \
  -F "file=@file.pdf"

# Track telemetry event
curl -X POST http://localhost:8000/telemetry/event \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"event_name":"button_click","category":"ui"}'

# Moderate text
curl -X POST http://localhost:8000/safety/moderate \
  -H "Content-Type: application/json" \
  -d '{"text":"Some content"}'

# List models
curl http://localhost:8000/chat/models
```
