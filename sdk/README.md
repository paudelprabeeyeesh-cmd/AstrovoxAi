# SDKs

Astrovox provides official SDKs for multiple languages, plus framework-specific
packages for React and Vue.

## Python

```python
import astrovox

client = astrovox.AstrovoxClient(api_key="your-key")
conversation = client.create_conversation(title="My Chat")
response = client.send_message(conversation.id, "Hello!")
print(response["ai_message"]["content"])
```

[Full Documentation](./python/README.md)

## TypeScript / JavaScript

```typescript
import { AstrovoxClient } from '@astrovox/sdk'

const client = new AstrovoxClient({ apiKey: 'your-key' })
const conversation = await client.createConversation({ title: 'My Chat' })
const response = await client.sendMessage({ conversationId: conversation.id, message: 'Hello!' })
console.log(response.ai_message.content)
```

[Full Documentation](./typescript/README.md)

## React

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

## Vue

```vue
<script setup>
import { AstrovoxChat } from '@astrovox/vue-sdk'
const apiKey = import.meta.env.VITE_ASTROVOX_API_KEY
</script>

<template>
  <AstrovoxChat :api-key="apiKey" theme="dark" />
</template>
```

## Go

```go
package main

import "github.com/astrovox/sdk/go"

client := astrovox.NewClient("your-key")
conversation, _ := client.CreateConversation("My Chat", "gpt-4")
response, _ := client.SendMessage(conversation.ID, "Hello!")
fmt.Println(response.AIMessage.Content)
```

[Full Documentation](./go/README.md)

## Rust

```rust
use astrovox_sdk::AstrovoxClient;

let client = AstrovoxClient::new("your-key", None);
let conversation = client.create_conversation("My Chat", "gpt-4").await?;
let response = client.send_message(&conversation.id, "Hello!").await?;
println!("{}", response.ai_message.content);
```

[Full Documentation](./rust/README.md)

## SDK Features

All SDKs support:

- Conversation management (create, list, delete)
- Message sending and streaming
- Multi-provider AI support (OpenAI, Anthropic, Gemini, Ollama)
- Agent creation and management
- Tool/plugin integration
- File uploads and RAG
- Webhook signature verification
- Typed error handling
- Retry logic with exponential backoff
- Request/response logging
