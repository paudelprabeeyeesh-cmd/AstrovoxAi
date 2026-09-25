# API Reference

## Base URL

```
https://api.astrovox.ai/v1
```

## Authentication

All API requests require a Bearer token:

```bash
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### POST /chat/message

Send a message and receive an AI response.

**Request:**
```json
{
  "conversation_id": "string",
  "message": "string",
  "model": "gpt-4"
}
```

**Response:**
```json
{
  "ai_message": {
    "id": "string",
    "role": "assistant",
    "content": "string",
    "created_at": "ISO8601"
  }
}
```

### POST /chat/stream

Stream a message response (Server-Sent Events).

### POST /conversations

Create a new conversation.

**Request:**
```json
{
  "title": "New Conversation",
  "model": "gpt-4"
}
```

**Response:**
```json
{
  "id": "string",
  "title": "string",
  "model": "string",
  "created_at": "ISO8601"
}
```

### GET /conversations

List all conversations for the authenticated user.

### DELETE /conversations/:id

Delete a conversation (soft delete).

### GET /health

Health check endpoint.

### POST /auth/login

Authenticate and receive an access token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Internal Server Error |

## Rate Limits

- Free tier: 100 requests/hour
- Pro tier: 1000 requests/hour
- Enterprise: Custom limits
