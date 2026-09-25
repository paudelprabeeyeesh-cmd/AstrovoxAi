# Examples

## Basic Chat

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

## Streaming Chat

```typescript
for await (const chunk of client.streamMessage({
  conversationId: conversation.id,
  message: 'Write a story',
  model: 'gpt-4'
})) {
  process.stdout.write(chunk)
}
```

## Python CLI

```python
import astrovox

client = astrovox.AstrovoxClient(api_key="your-key")
conv = client.create_conversation(title="Python Example")
response = client.send_message(conv.id, "Hello!")
print(response['ai_message']['content'])
```

## React Component

```tsx
import { AstrovoxChat } from '@astrovox/react-sdk'

export default function App() {
  return (
    <AstrovoxChat
      apiKey={process.env.NEXT_PUBLIC_ASTROVOX_API_KEY}
      theme="dark"
      enableVoice={true}
      enableBranching={true}
    />
  )
}
```

## Vue Component

```vue
<template>
  <AstrovoxChat :api-key="apiKey" theme="dark" />
</template>

<script setup>
import { AstrovoxChat } from '@astrovox/vue-sdk'
const apiKey = import.meta.env.VITE_ASTROVOX_API_KEY
</script>
```

## Web Component

```html
<script type="module" src="https://cdn.astrovox.ai/web-component.js"></script>
<astrovox-chat api-key="your-key" theme="dark"></astrovox-chat>
```

## iFrame Fallback

```html
<iframe
  src="https://chat.astrovox.ai/embed?apiKey=your-key"
  width="100%"
  height="600"
  frameborder="0"
></iframe>
```
