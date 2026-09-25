# Migration Guides

## Migrating from v1 to v2

### Breaking Changes

- `conversation_id` → `conversationId` in all API requests
- `created_at` → `createdAt` in responses
- Removed `/v1/chat` endpoint, use `/v1/chat/message` instead

### SDK Updates

#### Python

```python
# v1
client.chat(conversation_id, message)

# v2
client.send_message(conversation_id, message)
```

#### TypeScript

```typescript
// v1
await client.chat({ conversationId, message })

// v2
await client.sendMessage({ conversationId: conversation.id, message })
```

### Frontend

- `Chat.jsx` now uses `MessageContent` component
- Theme system uses CSS custom properties
- All components are now accessible (WCAG 2.2 AA)

### Database

Run the migration:

```bash
psql -U postgres -d astrovox -f migrations/v2.sql
```

## Migrating from OpenAI SDK

```typescript
// OpenAI SDK
import OpenAI from 'openai'
const openai = new OpenAI()

// Astrovox SDK
import { AstrovoxClient } from '@astrovox/sdk'
const client = new AstrovoxClient({ apiKey: 'astrovox-key' })
```

## Migrating from LangChain

```python
# LangChain
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

# Astrovox
import astrovox
client = astrovox.AstrovoxClient(api_key="your-key")
```
