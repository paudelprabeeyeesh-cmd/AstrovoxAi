# Migration Guides

Step-by-step guides for migrating to Astrovox AI from other platforms and upgrading between versions.

## Table of Contents

- [Migrating from v1 to v2](#migrating-from-v1-to-v2)
- [Migrating from OpenAI SDK](#migrating-from-openai-sdk)
- [Migrating from LangChain](#migrating-from-langchain)
- [Migrating from LlamaIndex](#migrating-from-llamaindex)
- [Migrating from Custom Solution](#migrating-from-custom-solution)

---

## Migrating from v1 to v2

### Breaking Changes

- `conversation_id` → `conversationId` in all API requests
- `created_at` → `createdAt` in responses
- Removed `/v1/chat` endpoint, use `/v1/chat/message` instead
- Authentication now uses Supabase JWT instead of custom tokens
- File uploads require multipart form data instead of base64

### Migration Steps

1. Update API endpoints
2. Update SDK method names
3. Update frontend components
4. Run database migration
5. Test thoroughly

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
- Routing updated to React Router v6

### Database

Run the migration:

```bash
psql -U postgres -d astrovox -f migrations/v2.sql
```

Or using Alembic:

```bash
cd 02-Backend
alembic upgrade head
```

### Rollback Plan

If issues arise, you can rollback:

```bash
alembic downgrade -1
```

---

## Migrating from OpenAI SDK

### TypeScript

```typescript
// OpenAI SDK
import OpenAI from 'openai'
const openai = new OpenAI()

const completion = await openai.chat.completions.create({
  model: 'gpt-4',
  messages: [{ role: 'user', content: 'Hello!' }],
})

// Astrovox SDK
import { AstrovoxClient } from '@astrovox/sdk'
const client = new AstrovoxClient({ apiKey: 'astrovox-key' })

const conversation = await client.createConversation({ title: 'Chat' })
const response = await client.sendMessage({
  conversationId: conversation.id,
  message: 'Hello!'
})
```

### Python

```python
# OpenAI SDK
from openai import OpenAI
openai = OpenAI()

completion = openai.chat.completions.create(
  model="gpt-4",
  messages=[{"role": "user", "content": "Hello!"}]
)

# Astrovox SDK
import astrovox
client = astrovox.AstrovoxClient(api_key="your-key")

conversation = client.create_conversation(title="Chat")
response = client.send_message(conversation.id, "Hello!")
```

### Key Differences

| Feature | OpenAI SDK | Astrovox SDK |
|---------|-----------|--------------|
| Multi-provider | No | Yes (OpenAI, Anthropic, Gemini, Ollama) |
| Memory | No | Yes (persistent context) |
| Conversations | Manual | Built-in management |
| Streaming | Manual | Built-in |
| Voice | No | Yes |
| File uploads | No | Yes |

---

## Migrating from LangChain

### Python

```python
# LangChain
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

chat = ChatOpenAI(model="gpt-4")
response = chat([HumanMessage(content="Hello!")])

# Astrovox
import astrovox
client = astrovox.AstrovoxClient(api_key="your-key")
conversation = client.create_conversation(title="LangChain Migration")
response = client.send_message(conversation.id, "Hello!")
```

### Key Differences

| Feature | LangChain | Astrovox |
|---------|-----------|----------|
| Abstraction | High-level chains | Direct API |
| Memory | Custom implementations | Built-in |
| Providers | Via integrations | Native support |
| Deployment | Self-hosted | Managed API |
| Cost | Pay for tokens | Tiered pricing |

---

## Migrating from LlamaIndex

```python
# LlamaIndex
from llama_index import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("What is this about?")

# Astrovox RAG
import astrovox
client = astrovox.AstrovoxClient(api_key="your-key")

# Upload documents for RAG
client.upload_documents(["data/file.pdf"])

# Query with RAG
conversation = client.create_conversation(
  title="RAG Chat",
  enable_rag=True
)
response = client.send_message(conversation.id, "What is this about?")
```

---

## Migrating from Custom Solution

### Assessment Checklist

Before migrating, document your current setup:

- [ ] Current AI providers and models
- [ ] Authentication method
- [ ] Database schema
- [ ] Message history format
- [ ] Custom features implemented
- [ ] Integration points (Slack, Discord, etc.)

### Migration Steps

1. **Data Export**: Export conversations and user data
2. **Schema Mapping**: Map your data model to Astrovox schema
3. **API Integration**: Replace direct AI calls with Astrovox SDK
4. **Auth Migration**: Migrate users to Supabase Auth
5. **Testing**: Parallel run to validate functionality
6. **Cutover**: Switch traffic to Astrovox
7. **Cleanup**: Decommission old infrastructure

### Data Format Conversion

```python
# Your format
{
  "user_id": "123",
  "messages": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello!"}
  ]
}

# Astrovox format
{
  "conversation": {
    "id": "uuid",
    "title": "Chat"
  },
  "messages": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello!"}
  ]
}
```

---

## Post-Migration Verification

After migration, verify:

- [ ] All conversations imported correctly
- [ ] Authentication works for existing users
- [ ] AI responses match expected quality
- [ ] Performance meets requirements
- [ ] Monitoring and alerts configured
- [ ] Documentation updated for team
- [ ] Old system decommissioned safely
