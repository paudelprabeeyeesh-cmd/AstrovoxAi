# TypeScript SDK

Official TypeScript/JavaScript SDK for Astrovox AI.

## Installation

```bash
npm install @astrovox/sdk
# or
yarn add @astrovox/sdk
# or
pnpm add @astrovox/sdk
```

## Quick Start

```typescript
import { AstrovoxClient } from '@astrovox/sdk'

const client = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY,
  baseUrl: 'https://api.astrovox.ai/v1'
})

// Create conversation
const conversation = await client.createConversation({
  title: 'My Conversation',
  model: 'gpt-4'
})

// Send message
const response = await client.sendMessage({
  conversationId: conversation.id,
  message: 'Hello, AI!'
})

console.log(response.ai_message.content)
```

## Streaming

```typescript
for await (const chunk of client.streamMessage({
  conversationId: conversation.id,
  message: 'Write a story',
  model: 'gpt-4'
})) {
  process.stdout.write(chunk)
}
```

## React Integration

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

## Vue Integration

```vue
<script setup>
import { AstrovoxChat } from '@astrovox/vue-sdk'
const apiKey = import.meta.env.VITE_ASTROVOX_API_KEY
</script>

<template>
  <AstrovoxChat :api-key="apiKey" theme="dark" />
</template>
```

## Error Handling

```typescript
import { AstrovoxClient, RateLimitError, AuthenticationError, AstrovoxError } from '@astrovox/sdk'

try {
  await client.sendMessage({ conversationId: '1', message: 'Hello' })
} catch (error) {
  if (error instanceof RateLimitError) {
    console.log('Rate limited. Retry after:', error.retryAfter)
  } else if (error instanceof AuthenticationError) {
    console.log('Invalid API key')
  } else if (error instanceof AstrovoxError) {
    console.log(`Error ${error.status}: ${error.message}`)
  }
}
```

## Configuration

```typescript
const client = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY,
  baseUrl: 'https://api.astrovox.ai/v1',
  timeout: 30000,
  retries: 3
})
```
