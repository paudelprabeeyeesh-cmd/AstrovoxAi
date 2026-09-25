# Examples Gallery

Real-world examples and use cases for Astrovox AI.

## Quick Examples

### Basic Chat

```typescript
import { AstrovoxClient } from '@astrovox/sdk'

const client = new AstrovoxClient({ apiKey: process.env.ASTROVOX_API_KEY })
const conversation = await client.createConversation({ title: 'Example Chat' })
const response = await client.sendMessage({
  conversationId: conversation.id,
  message: 'Explain quantum computing',
  model: 'gpt-4'
})
console.log(response.ai_message.content)
```

### Streaming Chat

```typescript
for await (const chunk of client.streamMessage({
  conversationId: conversation.id,
  message: 'Write a story',
  model: 'gpt-4'
})) {
  process.stdout.write(chunk)
}
```

### Python CLI

```python
import astrovox

client = astrovox.AstrovoxClient(api_key="your-key")
conv = client.create_conversation(title="Python Example")
response = client.send_message(conv.id, "Hello!")
print(response['ai_message']['content'])
```

### React Component

```tsx
import { AstrovoxChat } from '@astrovox/react-sdk'

export default function App() {
  return (
    <AstrovoxChat
      apiKey={process.env.NEXT_PUBLIC_ASTROVOX_API_KEY}
      theme="dark"
      enableVoice
      enableBranching
    />
  )
}
```

### Vue Component

```vue
<template>
  <AstrovoxChat :api-key="apiKey" theme="dark" />
</template>

<script setup>
import { AstrovoxChat } from '@astrovox/vue-sdk'
const apiKey = import.meta.env.VITE_ASTROVOX_API_KEY
</script>
```

### Web Component

```html
<script type="module" src="https://cdn.astrovox.ai/web-component.js"></script>
<astrovox-chat api-key="your-key" theme="dark"></astrovox-chat>
```

### iFrame Fallback

```html
<iframe
  src="https://chat.astrovox.ai/embed?apiKey=your-key"
  width="100%"
  height="600"
  frameborder="0"
></iframe>
```

---

## Use Cases

### Customer Support Bot

```typescript
const supportBot = await client.createAgent({
  name: 'Support Bot',
  model: 'gpt-4',
  systemPrompt: 'You are a helpful customer support agent for Acme Corp.',
  tools: ['knowledge_base', 'ticket_creation']
})

const response = await supportBot.chat('How do I reset my password?')
```

### Code Review Assistant

```python
review_assistant = client.create_agent(
    name="Code Reviewer",
    system_prompt="Review code for bugs, security issues, and best practices.",
    enable_code_execution=True
)

response = review_assistant.chat(f"Review this code:\n```python\n{code}\n```")
```

### Data Analysis Chat

```typescript
const analyst = await client.createAgent({
  name: 'Data Analyst',
  model: 'gpt-4',
  tools: ['sql_query', 'data_visualization'],
  systemPrompt: 'You are a data analyst. Help users query and visualize data.'
})

const response = await analyst.chat('Show me sales trends for Q3')
```

### Multi-Agent Workflow

```python
# Coordinate multiple specialized agents
workflow = client.create_workflow([
  {"agent": "researcher", "task": "Research topic X"},
  {"agent": "writer", "task": "Draft article based on research"},
  {"agent": "editor", "task": "Edit and polish the draft"}
])

result = workflow.execute()
```

### Voice-Enabled Assistant

```tsx
<AstrovoxChat
  apiKey={apiKey}
  theme="dark"
  enableVoice
  voiceProvider="elevenlabs"
  voiceId="your-voice-id"
/>
```

### Team Workspace

```typescript
const workspace = await client.createWorkspace({
  name: 'Engineering Team',
  members: ['user-1', 'user-2', 'user-3']
})

await workspace.shareConversation(conversationId)
await workspace.setPermissions('user-1', ['read', 'write', 'admin'])
```

### RAG with Custom Knowledge Base

```python
# Upload documents
client.upload_documents([
  "docs/manual.pdf",
  "docs/faq.md"
])

# Create RAG-enabled conversation
conv = client.create_conversation(
  title="Product Support",
  enable_rag=True,
  knowledge_base_ids=["kb-123"]
)

response = client.send_message(
  conv.id,
  "What are the warranty terms?"
)
```

---

## Advanced Examples

### Streaming with Custom UI

```tsx
function CustomStreamingChat() {
  const [messages, setMessages] = useState([])

  const sendMessage = async (content: string) => {
    const userMessage = { role: 'user', content }
    setMessages(prev => [...prev, userMessage])

    const assistantMessage = { role: 'assistant', content: '' }
    setMessages(prev => [...prev, assistantMessage])

    for await (const chunk of client.streamMessage({
      conversationId: conversation.id,
      message: content
    })) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1].content += chunk.delta
        return updated
      })
    }
  }
}
```

### Plugin Development

```python
from astrovox import AstrovoxPlugin

class WeatherPlugin(AstrovoxPlugin):
  name = "weather"
  version = "1.0.0"

  def get_weather(self, city: str) -> dict:
    # Your implementation
    return {"temp": 72, "condition": "sunny"}

  def register(self, client):
    client.register_tool("weather", self.get_weather)
```

### Webhook Integration

```typescript
// Handle Astrovox webhooks
app.post('/webhooks/astrovox', (req, res) => {
  const event = req.body

  switch (event.type) {
    case 'message.created':
      handleNewMessage(event.data)
      break
    case 'conversation.updated':
      handleConversationUpdate(event.data)
      break
    case 'agent.completed':
      handleAgentCompletion(event.data)
      break
  }

  res.sendStatus(200)
})
```

---

## Example Applications

### CLI Chat Tool

```python
#!/usr/bin/env python3
import astrovox
import sys
import os

client = astrovox.AstrovoxClient(api_key=os.environ["ASTROVOX_API_KEY"])
conv = client.create_conversation(title="CLI Chat")

print("Astrovox CLI Chat. Type 'quit' to exit.")
while True:
  user_input = input("\nYou: ")
  if user_input.lower() in ['quit', 'exit']:
    break

  response = client.send_message(conv.id, user_input)
  print(f"\nAI: {response['ai_message']['content']}")
```

### Slack Bot

```typescript
import { App } from '@slack/bolt'
import { AstrovoxClient } from '@astrovox/sdk'

const astrovox = new AstrovoxClient({ apiKey: process.env.ASTROVOX_API_KEY })
const slackApp = new App({ token: process.env.SLACK_TOKEN, signingSecret: process.env.SLACK_SIGNING_SECRET })

slackApp.event('app_mention', async ({ event, say }) => {
  const conversation = await astrovox.createConversation({
    title: `Slack: ${event.channel}`,
    metadata: { channel: event.channel, user: event.user }
  })

  const response = await astrovox.sendMessage({
    conversationId: conversation.id,
    message: event.text.replace(/<@.*?>/, '').trim()
  })

  await say(response.ai_message.content)
})
```

### Browser Extension

```typescript
// background.ts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'SUMMARIZE') {
    const client = new AstrovoxClient({ apiKey: request.apiKey })
    client.sendMessage({
      conversationId: request.conversationId,
      message: `Summarize: ${request.text}`
    }).then(sendResponse)
    return true
  }
})
```

### Scheduled Reports

```python
import schedule
import time

def generate_daily_report():
    response = client.send_message(
        conversation_id="report-conv",
        message="Generate a daily summary of yesterday's activities."
    )
    send_email("team@example.com", "Daily Report", response['ai_message']['content'])

schedule.every().day.at("09:00").do(generate_daily_report)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Multi-Provider Fallback

```typescript
const providers = [
  { provider: 'openai', model: 'gpt-4' },
  { provider: 'anthropic', model: 'claude-3-5-sonnet-20240620' },
  { provider: 'gemini', model: 'gemini-1.5-pro' }
]

for (const p of providers) {
  try {
    const response = await client.sendMessage({
      conversationId: conv.id,
      message: 'Hello',
      provider: p.provider,
      model: p.model
    })
    console.log(`Succeeded with ${p.provider}`)
    break
  } catch (error) {
    console.log(`Failed with ${p.provider}, trying next...`)
  }
}
```
