# Developer Platform Guide

## REST API

The AstrovoxAI REST API provides endpoints for chat completions, embeddings, models, and usage.

### Base URL
`https://api.astrovox.ai/v1`

### Authentication
Include the `Authorization` header with a Bearer token:
```bash
curl -H "Authorization: Bearer $ASTROVOX_API_KEY" https://api.astrovox.ai/v1/models
```

### Chat Completions
```bash
curl -X POST https://api.astrovox.ai/v1/chat/completions \
  -H "Authorization: Bearer $ASTROVOX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## GraphQL API

GraphQL endpoint: `https://api.astrovox.ai/graphql`

Example query:
```graphql
query {
  me {
    id
    email
    organizations {
      id
      name
    }
  }
}
```

## SDKs

Official SDKs are available for Python, TypeScript, Go, Java, Rust, and C#.

### Python
```bash
pip install astrovox
```

```python
from sdk.python.astrovox import AstrovoxClient

client = AstrovoxClient(api_key="...")
conversation = client.create_conversation(title="Demo")
response = client.send_message(conversation.id, "Hello")
```

### TypeScript
```bash
npm install @astrovox/sdk
```

```typescript
import { AstrovoxClient } from '@astrovox/sdk';
const client = new AstrovoxClient('...');
const conv = await client.createConversation({ title: 'Demo' });
const resp = await client.sendMessage({ conversationId: conv.id, message: 'Hello' });
```

## Plugin System

Plugins are Python modules with a `manifest.json`.

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "entrypoint": "plugin.py",
  "hooks": [
    {"name": "on_request", "event": "request.received"}
  ]
}
```

Register via:
```bash
curl -X POST https://api.astrovox.ai/v1/plugins/register \
  -H "Authorization: Bearer $ASTROVOX_API_KEY" \
  -F manifest=@manifest.json
```

## Webhooks

Register a webhook to receive events:
```bash
curl -X POST https://api.astrovox.ai/v1/webhooks \
  -H "Authorization: Bearer $ASTROVOX_API_KEY" \
  -d '{"url": "https://example.com/hook", "events": ["evaluation.completed"]}'
```

## Custom Tools

Tools can be registered and invoked by agents:

```python
from app.api.custom_tools import tool_registry
tool_registry.register_tool("my_tool", "Does something", {"param": {"type": "string"}}, ["param"], handler=my_func)
```

## Agent SDK

Build custom agents using the Agent SDK:
```python
from app.api.agent_sdk import agent_sdk
agent = agent_sdk.create_agent({"name": "my-agent", "role": "planner", "system_prompt": "..."})
result = agent_sdk.run_agent("my-agent", "Build a TODO app")
```

## Event System

Subscribe to events:
```python
from app.api.event_system import event_bus
def handler(event):
    print(event)
event_bus.subscribe("evaluation.completed", handler)
```
