# Contract Tests

Contract tests verify that the API matches the expected interface.

## Running Contract Tests

```bash
npm run test:contract
```

## API Contracts

### POST /chat/message
Request: `{ conversation_id: string, message: string, model?: string }`
Response: `{ ai_message: { id, role, content, created_at } }`

### POST /conversations
Request: `{ title?: string, model?: string }`
Response: `{ id, title, model, created_at }`

### GET /conversations
Response: `Conversation[]`

## Client SDK Contracts

### Python SDK
```python
client = AstrovoxClient(api_key="...")
client.send_message(conv_id, message)
client.create_conversation(title="...")
```

### TypeScript SDK
```typescript
const client = new AstrovoxClient({ apiKey: "..." })
await client.sendMessage({ conversationId, message })
await client.createConversation({ title })
```

## Breaking Changes

When modifying API contracts:
1. Update OpenAPI spec
2. Regenerate SDKs
3. Update all tests
4. Update migration guides
