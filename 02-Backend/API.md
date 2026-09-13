# AstrovoxAI API

## Authentication
Include `Authorization: Bearer astrovox-<key>` in every request.

## Endpoints

### POST /v1/solve
Request:
```json
{ "text": "your question" }
```
Response:
```json
{
  "result": "answer",
  "model": "gpt-4o-mini",
  "cost_usd": 0.0005,
  "cached": false,
  "memories_used": []
}
```

### POST /v1/memory
Request:
```json
{ "key": "color", "value": "blue" }
```

### GET /v1/memory?user_id=me
Returns all memories.

### POST /v1/conversations
Request:
```json
{ "title": "My chat" }
```

### GET /v1/conversations
Returns all conversations.

### GET /v1/conversations/{id}/messages
Returns messages in a conversation.

### POST /v1/templates
Request:
```json
{ "name": "My template", "prompt": "Translate {{text}} to Spanish", "variables": "text" }
```

### GET /v1/templates
Returns all templates.

### POST /v1/knowledge
Request:
```json
{ "title": "Doc", "content": "Full text..." }
```

### GET /v1/knowledge/search?q=query
Searches knowledge base.

### POST /v1/feedback
Request:
```json
{ "request_id": "abc", "rating": 5, "comment": "Great" }
```

### GET /v1/metrics
Returns usage and revenue.

### GET /v1/health
Returns status.
