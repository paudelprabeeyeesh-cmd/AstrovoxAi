# OpenAPI Examples

Example requests and responses for the AstrovoxAI API.

## Health

### GET /health

Request:
```http
GET /health HTTP/1.1
Host: localhost:8000
```

Response 200:
```json
{
  "status": "healthy",
  "service": "astravox-ai-backend",
  "version": "2.0.0"
}
```

## Authentication

### POST /auth/login

Request:
```http
POST /auth/login HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

Response 200:
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

Response 401:
```json
{
  "detail": "Invalid credentials"
}
```

### POST /auth/signup

Request:
```http
POST /auth/signup HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

Response 200:
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

## Chat

### POST /chat/conversations

Request:
```http
POST /chat/conversations HTTP/1.1
Host: localhost:8000
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "Casual Conversation",
  "model": "gpt-4"
}
```

Response 200:
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

### POST /chat/message

Request:
```http
POST /chat/message HTTP/1.1
Host: localhost:8000
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "conversation_id": 1,
  "message": "What is the capital of France?",
  "model": "gpt-4"
}
```

Response 200:
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

## Memory

### POST /memory/save

Request:
```http
POST /memory/save HTTP/1.1
Host: localhost:8000
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "User prefers concise responses",
  "importance": 2
}
```

Response 200:
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

## Telemetry

### POST /telemetry/event

Request:
```http
POST /telemetry/event HTTP/1.1
Host: localhost:8000
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "event_name": "feature_used",
  "category": "feature",
  "metadata": {
    "feature": "memory_save",
    "duration_ms": 250
  }
}
```

Response 200:
```json
{
  "status": "OK",
  "event_id": 123,
  "message": "Event tracked successfully"
}
```

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

### 404 Not Found

```json
{
  "detail": "Conversation not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to process request: error message"
}
```
