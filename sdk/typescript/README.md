# TypeScript SDK

Official TypeScript SDK for Astrovox AI.

## Installation

```bash
npm install @astrovox/sdk
# or
yarn add @astrovox/sdk
# or
pnpm add @astrovox/sdk
```

## Usage

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

## Error Handling

```typescript
import { AstrovoxClient, RateLimitError, AuthenticationError } from '@astrovox/sdk'

try {
  await client.sendMessage({ conversationId: '1', message: 'Hello' })
} catch (error) {
  if (error instanceof RateLimitError) {
    console.log('Rate limited. Retry after:', error.retryAfter)
  } else if (error instanceof AuthenticationError) {
    console.log('Invalid API key')
  }
}
```
