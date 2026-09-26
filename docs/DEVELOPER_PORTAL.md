# Developer Portal

The Developer Portal is the unified control plane for AstrovoxAI ecosystem participants.

## Access

Open `frontend/developer.html` in your browser, or run:

```bash
astrovox portal open
```

## Features

### API Keys

Create, rotate, and revoke API keys. Scope keys to specific endpoints and set expiration.

```bash
astrovox keys create --name "production" --scopes "chat,agents"
astrovox keys revoke <key_id>
```

### Webhooks

Manage incoming and outgoing webhooks with HMAC-SHA256 signature verification.

```bash
astrovox webhooks create --url https://example.com/hook --events "message.created,agent.finished"
astrovox webhooks deliveries <webhook_id>
```

### Playground

Send live requests against `/v1/*` endpoints with auto-generated auth headers.

### Logs

Tail API request logs filtered by endpoint, status, or API key.

### Integrations

Connect GitHub, Slack, Discord, Notion, Jira, and cloud storage providers via OAuth 2.0.

## CLI Reference

| Command | Description |
|---------|-------------|
| `astrovox portal open` | Open portal in browser |
| `astrovox keys list` | List API keys |
| `astrovox keys create` | Create a new key |
| `astrovox webhooks list` | List webhooks |
| `astrovox integrations connect` | Connect a provider |
| `astrovox logs tail` | Tail API logs |

## Configuration

Environment variables:

```bash
ASTROVOX_API_KEY=your-key
ASTROVOX_BASE_URL=https://api.astrovox.ai/v1
ASTROVOX_PORTAL_THEME=dark
```
