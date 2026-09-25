# API Reference

Comprehensive reference for the Astrovox AI REST API.

> **Note:** For the legacy endpoint listing, see [API_REFERENCE.md](./API_REFERENCE.md).
> This document focuses on the v1 public API surface with request/response schemas.

## Base URL

```
Development: http://localhost:8000/v1
Production: https://api.astrovox.ai/v1
```

## Authentication

All API requests require a Bearer token in the Authorization header:

```bash
Authorization: Bearer YOUR_API_KEY
```

Obtain an API key via the dashboard or `/auth/login` endpoint.

## Rate Limits

| Tier | Requests per Hour | Burst |
|------|-------------------|-------|
| Free | 100 | 10 |
| Pro | 1,000 | 50 |
| Enterprise | Custom | Custom |

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

## Pagination

List endpoints support cursor-based pagination:

```
GET /conversations?limit=20&cursor=eyJpZCI6MTIzfQ
```

Response includes:
```json
{
  "data": [...],
  "next_cursor": "eyJpZCI6MTQ0fQ",
  "has_more": true
}
```

## Error Codes

| Code | Description | Retry-After |
|------|-------------|-------------|
| 400 | Bad Request | - |
| 401 | Unauthorized | - |
| 403 | Forbidden | - |
| 404 | Not Found | - |
| 409 | Conflict | - |
| 422 | Validation Error | - |
| 429 | Rate Limited | Yes |
| 500 | Internal Server Error | Yes (exponential backoff) |
| 503 | Service Unavailable | Yes |

## Endpoints

### POST /chat/message

Send a message and receive an AI response.

**Request:**
```json
{
  "conversation_id": "string",
  "message": "string",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false
}
```

**Response:**
```json
{
  "ai_message": {
    "id": "string",
    "role": "assistant",
    "content": "string",
    "model": "gpt-4",
    "created_at": "ISO8601",
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 50,
      "total_tokens": 60
    }
  }
}
```

### POST /chat/stream

Stream a message response (Server-Sent Events).

**Request:**
```json
{
  "conversation_id": "string",
  "message": "string",
  "model": "gpt-4"
}
```

**Response:**
```
Content-Type: text/event-stream

data: {"delta": "Hello"}
data: {"delta": " world"}
data: {"done": true}
```

### POST /conversations

Create a new conversation.

**Request:**
```json
{
  "title": "New Conversation",
  "model": "gpt-4",
  "system_prompt": "You are a helpful assistant."
}
```

**Response:**
```json
{
  "id": "string",
  "title": "string",
  "model": "string",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### GET /conversations

List all conversations for the authenticated user.

**Query Parameters:**
- `limit` (integer, default: 20, max: 100)
- `cursor` (string, optional)
- `sort` (string, default: "updated_at")

### GET /conversations/:id

Retrieve a specific conversation with messages.

### DELETE /conversations/:id

Delete a conversation (soft delete).

### POST /auth/login

Authenticate and receive an access token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600
}
```

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

### POST /auth/logout

Invalidate the current session.

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "ISO8601"
}
```

### GET /health/detailed

Detailed health check with dependency status.

### GET /metrics

Prometheus metrics endpoint.

## Webhooks

### POST /webhooks

Create a webhook subscription.

**Request:**
```json
{
  "url": "https://example.com/webhook",
  "events": ["message.created", "conversation.updated"],
  "secret": "webhook_secret"
}
```

### POST /webhooks/:id/verify

Verify webhook delivery.

## SDKs

Official SDKs are available for:
- [Python](./SDK_QUICKSTART.md#python)
- [TypeScript](./SDK_QUICKSTART.md#typescriptjavascript)
- [Go](./SDK_QUICKSTART.md#go)
- [Rust](./SDK_QUICKSTART.md#rust)

## Changelog

See [Changelog](./changelog.md) for API version history and breaking changes.

