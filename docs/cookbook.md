# Cookbook

## Common Patterns

### 1. Chat with Context

```python
import astrovox

client = astrovox.AstrovoxClient(api_key="your-key")
conv = client.create_conversation()

# Send initial message
client.send_message(conv.id, "My name is Alice")

# Follow-up with context
response = client.send_message(conv.id, "What's my name?")
print(response['ai_message']['content'])  # "Your name is Alice"
```

### 2. Streaming Response

```typescript
const stream = client.streamMessage({
  conversationId: conv.id,
  message: 'Write a poem',
})

for await (const chunk of stream) {
  process.stdout.write(chunk)
}
```

### 3. Multi-turn Conversation

```typescript
const messages = [
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: 'Hello!' },
  { role: 'assistant', content: 'Hi there! How can I help?' },
  { role: 'user', content: 'Tell me a joke' }
]

for (const msg of messages) {
  if (msg.role === 'user') {
    await client.sendMessage({ conversationId: conv.id, message: msg.content })
  }
}
```

### 4. Error Handling

```python
import astrovox
from astrovox.errors import RateLimitError, AuthenticationError

client = astrovox.AstrovoxClient(api_key="your-key")

try:
    response = client.send_message(conv.id, "Hello")
except RateLimitError:
    print("Rate limited. Retry after 60 seconds.")
except AuthenticationError:
    print("Invalid API key.")
except Exception as e:
    print(f"Error: {e}")
```

### 5. Batch Processing

```typescript
const conversations = await client.listConversations()
for (const conv of conversations) {
  const response = await client.sendMessage({
    conversationId: conv.id,
    message: 'Summarize this conversation'
  })
  console.log(`${conv.title}: ${response.ai_message.content}`)
}
```

## Recipes

### Recipe: Summarize All Conversations

```python
for conv in client.list_conversations():
    for msg in conv.messages:
        summary = client.send_message(conv.id, f"Summarize: {msg.content}")
        print(f"{conv.title}: {summary}")
```

### Recipe: Export to Markdown

```typescript
const conv = await client.getConversation(id)
const markdown = conv.messages.map(m => `## ${m.role}\n\n${m.content}`).join('\n\n')
fs.writeFileSync(`${conv.title}.md`, markdown)
```
