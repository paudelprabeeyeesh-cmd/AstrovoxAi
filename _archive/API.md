# ASTRAVOX PRIME - API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

All protected endpoints require an `Authorization` header with a Bearer token:

```
Authorization: Bearer <access_token>
```

## Health Endpoints

### Check API Health

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "astravox-ai-backend",
  "version": "2.0.0"
}
```

### Readiness Probe

```http
GET /health/readiness
```

Response:
```json
{
  "status": "ready",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Authentication Endpoints

### Sign Up

```http
POST /auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

Response:
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

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

Response:
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

### Logout

```http
POST /auth/logout
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "message": "Logout successful. Please clear your session tokens on the client."
}
```

### Reset Password

```http
POST /auth/reset-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

Response:
```json
{
  "status": "OK",
  "message": "Password reset email sent successfully"
}
```

### Get Current User

```http
GET /auth/me
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "profile": {
      "id": "uuid",
      "username": "johndoe",
      "full_name": "John Doe",
      "avatar_url": null,
      "role": "user",
      "tier": "free"
    }
  }
}
```

## Chat Endpoints

### Create Conversation

```http
POST /chat/conversations
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "Casual Conversation",
  "model": "optimus-3,5"
}
```

Response:
```json
{
  "status": "OK",
  "conversation": {
    "id": 1,
    "user_id": "uuid",
    "title": "Casual Conversation",
    "model": "optimus-3,5",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

### List Conversations

```http
GET /chat/conversations?limit=50&offset=0
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "conversations": [
    {
      "id": 1,
      "user_id": "uuid",
      "title": "Casual conversation",
      "model": "optimus-3,5",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "count": 1
}
```

### Get Conversation

```http
GET /chat/conversations/{conversation_id}
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "conversation": {
    "id": 1,
    "user_id": "uuid",
    "title": "Casual conversation",
    "model": "optimus-3,5",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

### Get Messages

```http
GET /chat/conversations/{conversation_id}/messages?limit=100&offset=0
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "messages": [
    {
      "id": 1,
      "conversation_id": 1,
      "user_id": "uuid",
      "role": "user",
      "content": "Hello, how are you?",
      "created_at": "2024-01-01T12:00:00Z"
    },
    {
      "id": 2,
      "conversation_id": 1,
      "user_id": "uuid",
      "role": "assistant",
      "content": "I'm doing well, thank you for asking!",
      "created_at": "2024-01-01T12:00:01Z"
    }
  ],
  "count": 2
}
```

### Send Message

```http
POST /chat/message
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "conversation_id": 1,
  "message": "What is the capital of France?",
  "model": "optimus-3,5"
}
```

Response:
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

### Delete Conversation

```http
DELETE /chat/conversations/{conversation_id}
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "message": "Conversation deleted successfully"
}
```

## Memory Endpoints

### Save Memory

```http
POST /memory/save
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "User prefers concise responses",
  "importance": 2
}
```

Response:
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

### Get Memory

```http
GET /memory?limit=50
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "memory": [
    {
      "id": 1,
      "user_id": "uuid",
      "content": "User prefers concise responses",
      "importance": 2,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "count": 1
}
```

### Get Memory Context

```http
POST /memory/context?limit=5
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "context": "User Context/Memory:\n- User prefers concise responses\n- User is interested in AI",
  "memory_count": 2
}
```

## API Endpoints

### API Status

```http
GET /api/status
```

Response:
```json
{
  "status": "OK",
  "service": "Astrovox-Ai-Api",
  "version": "2.0.0",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Get User Info

```http
GET /api/me
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "user": {
    "id": "uuid",
    "profile": {
      "id": "uuid",
      "username": "johndoe",
      "full_name": "John Doe",
      "role": "user",
      "tier": "free"
    }
  }
}
```

### Get User Stats

```http
GET /api/stats
Authorization: Bearer <access_token>
```

Response:
```json
{
  "status": "OK",
  "stats": {
    "total_conversations": 5,
    "total_memory_entries": 10,
    "user_tier": "free",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

## Telemetry Endpoints

### Track Custom Event

```http
POST /telemetry/event
Authorization: ******
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

Response:
```json
{
  "status": "OK",
  "event_id": 123,
  "message": "Event tracked successfully"
}
```

### Track Page View

```http
POST /telemetry/page-view
Authorization: ******
Content-Type: application/json

{
  "page": "/dashboard",
  "referrer": "/chat"
}
```

Response:
```json
{
  "status": "OK",
  "event_id": 124,
  "message": "Page view tracked"
}
```

### Track Error

```http
POST /telemetry/error
Authorization: ******
Content-Type: application/json

{
  "error_name": "APIError",
  "error_message": "Failed to fetch conversations",
  "stack_trace": "Error: ...",
  "context": {
    "endpoint": "/chat/conversations",
    "status_code": 500
  }
}
```

Response:
```json
{
  "status": "OK",
  "event_id": 125,
  "message": "Error tracked"
}
```

### Track User Action

```http
POST /telemetry/user-action
Authorization: ******
Content-Type: application/json

{
  "action": "message_sent",
  "category": "chat",
  "metadata": {
    "conversation_id": 1,
    "message_length": 42
  }
}
```

Response:
```json
{
  "status": "OK",
  "event_id": 126,
  "message": "User action tracked"
}
```

### Get Telemetry Stats

```http
GET /telemetry/stats?limit=100&offset=0
Authorization: ******
```

Response:
```json
{
  "status": "OK",
  "user_id": "uuid",
  "total_events": 150,
  "event_counts": {
    "message_sent": 45,
    "page_view": 60,
    "feature_used": 30,
    "error": 15
  },
  "category_counts": {
    "chat": 45,
    "navigation": 60,
    "feature": 30,
    "error": 15
  },
  "recent_events": [
    {
      "id": 150,
      "event_name": "page_view",
      "category": "navigation",
      "timestamp": "2024-01-01T12:05:00Z"
    }
  ],
  "offset": 0,
  "limit": 100
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

## Rate Limiting

Currently, there are no rate limits implemented. Rate limiting will be added in future versions.

## Pagination

List endpoints support pagination with the following query parameters:

- `limit`: Number of items to return (default: 50, max: 1000)
- `offset`: Number of items to skip (default: 0)

Example:
```http
GET /chat/conversations?limit=20&offset=40
```

## Versioning

The API version is included in the response headers:

```
X-API-Version: 2.0.0
```

Current version: **2.0.0**

## Support

For API support, please contact the development team. 
