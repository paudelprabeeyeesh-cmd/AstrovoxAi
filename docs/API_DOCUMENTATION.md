# API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

## Endpoints

### Health

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "astravox-ai-backend",
  "version": "2.0.0"
}
```

#### GET /health/readiness
Kubernetes readiness probe.

#### GET /health/liveness
Kubernetes liveness probe.

---

### Authentication

#### POST /auth/signup
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

**Response 200:**
```json
{
  "status": "OK",
  "message": "User registered successfully. Please verify your email.",
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

#### POST /auth/login
Login and get access tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response 200:**
```json
{
  "status": "OK",
  "message": "Login successful",
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  },
  "session": {
    "access_token": "token",
    "refresh_token": "refresh_token"
  }
}
```

#### POST /auth/logout
Logout current session.

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:**
```json
{
  "status": "OK",
  "message": "Logged out successfully"
}
```

#### POST /auth/reset-password
Request password reset.

**Request:**
```json
{
  "email": "user@example.com"
}
```

#### POST /auth/refresh
Refresh access token.

**Request:**
```json
{
  "refresh_token": "refresh_token"
}
```

#### GET /auth/me
Get current user profile.

**Headers:** `Authorization: Bearer <access_token>`

---

### Chat

#### POST /chat/conversations
Create a new conversation.

**Request:**
```json
{
  "title": "Casual Conversation",
  "model": "gpt-4"
}
```

**Response 200:**
```json
{
  "status": "OK",
  "conversation": {
    "id": 1,
    "user_id": "uuid",
    "title": "Casual Conversation",
    "model": "gpt-4",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

#### GET /chat/conversations
List conversations (paginated).

**Query Parameters:**
- `limit` (default: 50, max: 200)
- `offset` (default: 0)
- `pinned` (default: false)
- `archived` (default: false)
- `folder` (optional)

#### GET /chat/conversations/{id}
Get conversation details.

#### POST /chat/message
Send a message in a conversation.

**Request:**
```json
{
  "conversation_id": 1,
  "message": "What is the capital of France?",
  "model": "gpt-4"
}
```

**Response 200:**
```json
{
  "status": "OK",
  "user_message": {
    "id": 3,
    "conversation_id": 1,
    "role": "user",
    "content": "What is the capital of France?",
    "created_at": "2024-01-01T12:00:02Z"
  },
  "ai_message": {
    "id": 4,
    "conversation_id": 1,
    "role": "assistant",
    "content": "The capital of France is Paris.",
    "created_at": "2024-01-01T12:00:03Z"
  },
  "tokens_used": 45
}
```

#### DELETE /chat/conversations/{id}
Delete a conversation.

#### POST /chat/stream
Stream a chat response (Server-Sent Events).

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: text/event-stream
```

**Response:**
```
data: {"token": "The"}

data: {"token": " capital"}

data: {"token": " of"}

data: {"token": " France"}

data: {"token": " is"}

data: {"token": " Paris."}

data: [DONE]
```

---

### Memory

#### POST /memory/save
Save a memory entry.

**Request:**
```json
{
  "content": "User prefers concise responses",
  "importance": 2
}
```

**Response 200:**
```json
{
  "status": "OK",
  "memory": {
    "id": 1,
    "user_id": "uuid",
    "content": "User prefers concise responses",
    "importance": 2,
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

#### GET /memory
List memory entries.

#### POST /memory/context
Get memory context for a query.

---

### RAG

#### POST /rag/ingest
Ingest a document.

**Request:** `multipart/form-data`
```
file: @document.pdf
```

#### GET /rag/search
Search documents.

**Query Parameters:**
- `q` (required): Search query

---

### Models

#### GET /models
List available LLM models.

#### POST /models/select
Select a model for a conversation.

---

### Telemetry

#### POST /telemetry/event
Track custom event.

**Request:**
```json
{
  "event_name": "feature_used",
  "category": "feature",
  "metadata": {
    "feature": "memory_save",
    "duration_ms": 250
  }
}
```

#### POST /telemetry/page-view
Track page view.

#### POST /telemetry/error
Track error.

#### POST /telemetry/user-action
Track user action.

#### GET /telemetry/stats
Get telemetry stats.

---

### Admin

#### GET /admin/stats
System statistics (admin only).

#### GET /admin/users
List users (admin only).

---

### Metrics

#### GET /metrics
Prometheus metrics endpoint.

**Response:**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/health",status="200"} 1234
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authorization header required"
}
```

### 403 Forbidden
```json
{
  "detail": "Email not verified"
}
```

### 404 Not Found
```json
{
  "detail": "Conversation not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded. Retry after 60 seconds."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to process request: error message"
}
```

---

## OpenAPI Schema

Download the full OpenAPI schema:
```
GET /openapi.json
```

Interactive docs:
```
GET /docs       (Swagger UI)
GET /redoc      (ReDoc)
```
