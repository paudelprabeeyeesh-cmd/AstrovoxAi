# ASTROVOX AI — API REFERENCE

## Base URL
```
Development: http://localhost:8000
Production: https://api.astrovox.ai
```

## Authentication
All endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <supabase_jwt_token>
```

---

## Authentication Endpoints

### POST /auth/signup
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "status": "OK",
  "message": "User registered successfully",
  "user": {"id": "uuid", "email": "user@example.com"}
}
```

### POST /auth/login
Login with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "status": "OK",
  "user": {"id": "uuid", "email": "user@example.com"},
  "session": {"access_token": "jwt", "refresh_token": "jwt"}
}
```

### POST /auth/logout
Logout (client-side token cleanup).

### POST /auth/reset-password
Send password reset email.

### GET /auth/me
Get current user profile.

### POST /auth/refresh
Refresh access token.

---

## Chat Endpoints

### POST /chat/conversations
Create a new conversation.

**Request:**
```json
{
  "title": "My Conversation",
  "model": "gpt-4"
}
```

### GET /chat/conversations
List user's conversations.

### GET /chat/conversations/{id}
Get conversation details.

### GET /chat/conversations/{id}/messages
Get messages from a conversation.

### POST /chat/message
Send a message (supports streaming).

**Request:**
```json
{
  "conversation_id": 1,
  "message": "Hello, how are you?",
  "model": "gpt-4",
  "stream": false
}
```

**Response (non-streaming):**
```json
{
  "status": "OK",
  "user_message": {...},
  "ai_message": {...},
  "tokens_used": 42,
  "provider": "openai"
}
```

**Response (streaming — SSE):**
```
data: Hello
data: ! How
data: can I help?
data: [DONE]
```

### GET /chat/models
List all available models.

### POST /chat/conversations/{id}/title
Update conversation title.

### DELETE /chat/conversations/{id}
Delete a conversation.

---

## Memory Endpoints

### POST /memory/save
Save a memory entry.

**Request:**
```json
{
  "content": "User prefers Python over JavaScript",
  "importance": 2
}
```

### GET /memory/
Get user's memory entries.

### POST /memory/extract-from-conversation
Extract memories from a conversation.

### POST /memory/context
Get formatted memory context for AI.

### POST /memory/auto-extract
LLM-powered memory extraction.

---

## Embeddings Endpoints

### POST /embeddings/
Generate batch embeddings.

**Request:**
```json
{
  "texts": ["Hello world", "How are you?"],
  "model": "models/embedding-001"
}
```

**Response:**
```json
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
  "model": "models/embedding-001",
  "count": 2
}
```

### POST /embeddings/one
Generate single embedding.

### GET /embeddings/status
Check embedding service status.

---

## Knowledge Base Endpoints

### POST /knowledge/upload
Upload a document.

**Request:**
```json
{
  "filename": "notes.txt",
  "content": "Document content here...",
  "file_type": "text"
}
```

### POST /knowledge/search
Search the knowledge base.

**Request:**
```json
{
  "query": "What is machine learning?",
  "limit": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "content": "Machine learning is...",
      "score": 0.89,
      "document_id": "abc123",
      "filename": "notes.txt"
    }
  ],
  "count": 1
}
```

### GET /knowledge/documents
List user's documents.

### DELETE /knowledge/documents/{id}
Delete a document.

### GET /knowledge/stats
Get knowledge base statistics.

---

## Agent Endpoints

### POST /agent/tasks
Create an agent task.

**Request:**
```json
{
  "goal": "Research AI news, summarize it, and save to memory"
}
```

**Response:**
```json
{
  "task": {
    "id": "abc123",
    "goal": "Research AI news...",
    "state": "executing",
    "steps": [
      {"step_number": 1, "action": "search", "description": "Search for AI news"},
      {"step_number": 2, "action": "summarize", "description": "Summarize findings"}
    ]
  }
}
```

### POST /agent/tasks/{id}/execute
Execute a task.

### GET /agent/tasks
List all tasks.

### GET /agent/tasks/{id}
Get task details.

### GET /agent/tools
List available tools.

---

## Analytics Endpoints

### GET /analytics/dashboard
Get dashboard data.

### GET /analytics/usage?days=7
Get usage statistics.

### GET /analytics/providers
Get provider breakdown.

### GET /analytics/costs
Get cost estimates.

### GET /analytics/daily?days=30
Get daily usage.

---

## Monitoring Endpoints

### GET /monitoring/health/detailed
Detailed health check with system stats.

### GET /monitoring/errors
Get tracked errors.

### GET /monitoring/performance
Get performance statistics.

### GET /monitoring/uptime
Get application uptime.

### GET /monitoring/dashboard
Complete monitoring dashboard.

---

## Security Endpoints

### GET /security/audit
Run full security audit.

### GET /security/check/environment
Check environment security.

---

## System Endpoints

### GET /
API root with available endpoints.

### GET /health
Health check.

### GET /health/readiness
Kubernetes readiness probe.

### GET /health/liveness
Kubernetes liveness probe.

### GET /metrics
Prometheus metrics.

---

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error description"
}
```

| Status | Description |
|--------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Internal Server Error |
| 502 | Bad Gateway (provider error) |
| 503 | Service Unavailable |
