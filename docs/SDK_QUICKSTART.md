# SDK Quickstart

Get up and running with Astrovox AI SDKs in minutes.

## Available SDKs

- [Python](#python)
- [TypeScript/JavaScript](#typescriptjavascript)
- [React](#react)
- [Vue](#vue)
- [Go](#go)
- [Rust](#rust)

---

## Python

### Installation

```bash
pip install astrovox
```

### Quick Start

```python
import os
from astrovox import AstrovoxClient

client = AstrovoxClient(api_key=os.environ["ASTROVOX_API_KEY"])

# Create a conversation
conversation = client.create_conversation(title="My First Chat")

# Send a message
response = client.send_message(conversation.id, "Hello, AI!")
print(response["ai_message"]["content"])

# Stream a response
for chunk in client.stream_message(conversation.id, "Tell me a story"):
    print(chunk, end="", flush=True)
```

### Advanced Usage

```python
from astrovox import AstrovoxClient, Agent, Tool

client = AstrovoxClient(api_key=os.environ["ASTROVOX_API_KEY"])

# Create an agent with tools
agent = client.create_agent(
    name="Assistant",
    model="gpt-4",
    tools=["web_search", "code_execution"],
    system_prompt="You are a helpful assistant."
)

response = agent.chat("What's the weather in San Francisco?")

# Upload documents for RAG
client.upload_documents(["manual.pdf", "faq.md"])
conversation = client.create_conversation(
    title="Support Chat",
    enable_rag=True
)
```

### Error Handling

```python
from astrovox import AstrovoxError, RateLimitError, AuthenticationError

try:
    response = client.send_message(conversation.id, "Hello")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except AuthenticationError:
    print("Invalid API key")
except AstrovoxError as e:
    print(f"Error {e.status}: {e.message}")
```

### CLI

```bash
astrovox send <conversation_id> "Hello, AI!"
astrovox conversations
astrovox create --title "New Chat"
astrovox health
```

---

## TypeScript / JavaScript

### Installation

```bash
npm install @astrovox/sdk
# or
yarn add @astrovox/sdk
# or
pnpm add @astrovox/sdk
```

### Quick Start

```typescript
import { AstrovoxClient } from '@astrovox/sdk'

const client = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY!
})

// Create a conversation
const conversation = await client.createConversation({
  title: 'My First Chat'
})

// Send a message
const response = await client.sendMessage({
  conversationId: conversation.id,
  message: 'Hello, AI!'
})
console.log(response.ai_message.content)

// Stream a response
for await (const chunk of client.streamMessage({
  conversationId: conversation.id,
  message: 'Tell me a story'
})) {
  process.stdout.write(chunk)
}
```

### React Integration

```tsx
import { AstrovoxChat } from '@astrovox/react-sdk'

export default function App() {
  return (
    <AstrovoxChat
      apiKey={process.env.NEXT_PUBLIC_ASTROVOX_API_KEY!}
      theme="dark"
      enableVoice
      enableBranching
    />
  )
}
```

### Vue Integration

```vue
<script setup>
import { AstrovoxChat } from '@astrovox/vue-sdk'
const apiKey = import.meta.env.VITE_ASTROVOX_API_KEY
</script>

<template>
  <AstrovoxChat :api-key="apiKey" theme="dark" />
</template>
```

### Error Handling

```typescript
import { AstrovoxClient, AstrovoxError, RateLimitError, AuthenticationError } from '@astrovox/sdk'

try {
  const response = await client.sendMessage({
    conversationId: conversation.id,
    message: 'Hello'
  })
} catch (err) {
  if (err instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${err.retryAfter}s`)
  } else if (err instanceof AuthenticationError) {
    console.error('Invalid API key')
  } else if (err instanceof AstrovoxError) {
    console.error(`Error ${err.status}: ${err.message}`)
  }
}
```

---

## React

### Installation

```bash
npm install @astrovox/react-sdk @astrovox/sdk
```

### Basic Usage

```tsx
import { AstrovoxChat } from '@astrovox/react-sdk'

export default function App() {
  return (
    <AstrovoxChat
      apiKey={process.env.NEXT_PUBLIC_ASTROVOX_API_KEY}
      theme="dark"
      enableVoice
      enableBranching
      enableFileUpload
    />
  )
}
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `apiKey` | `string` | required | Your Astrovox API key |
| `theme` | `'dark' \| 'light' \| 'high-contrast'` | `'dark'` | UI theme |
| `model` | `string` | `'gpt-4'` | Default AI model |
| `enableVoice` | `boolean` | `false` | Enable voice input/output |
| `enableBranching` | `boolean` | `false` | Enable conversation branching |
| `enableFileUpload` | `boolean` | `true` | Enable file uploads |
| `placeholder` | `string` | `'Type your message...'` | Input placeholder |
| `height` | `string \| number` | `'600px'` | Component height |
| `onMessageSent` | `(message: Message) => void` | - | Called when user sends a message |
| `onMessageReceived` | `(message: Message) => void` | - | Called when AI responds |
| `onError` | `(error: Error) => void` | - | Called on error |

---

## Vue

### Installation

```bash
npm install @astrovox/vue-sdk @astrovox/sdk
```

### Basic Usage

```vue
<script setup>
import { AstrovoxChat } from '@astrovox/vue-sdk'
const apiKey = import.meta.env.VITE_ASTROVOX_API_KEY
</script>

<template>
  <AstrovoxChat :api-key="apiKey" theme="dark" />
</template>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `apiKey` | `string` | required | Your Astrovox API key |
| `theme` | `string` | `'dark'` | UI theme |
| `model` | `string` | `'gpt-4'` | Default AI model |
| `placeholder` | `string` | `'Type your message...'` | Input placeholder |
| `height` | `string` | `'600px'` | Component height |

---

## Go

### Installation

```bash
go get github.com/astrovox/sdk/go
```

### Quick Start

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    astrovox "github.com/astrovox/sdk/go"
)

func main() {
    client := astrovox.NewClient(astrovox.Config{
        APIKey: os.Getenv("ASTROVOX_API_KEY"),
    })

    conversation, err := client.CreateConversation(context.Background(), &astrovox.CreateConversationRequest{
        Title: "My First Chat",
    })
    if err != nil {
        log.Fatal(err)
    }

    response, err := client.SendMessage(context.Background(), &astrovox.SendMessageRequest{
        ConversationID: conversation.ID,
        Message:        "Hello, AI!",
    })
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(response.AIMessage.Content)
}
```

---

## Rust

### Installation

```toml
# Cargo.toml
[dependencies]
astrovox-sdk = "0.1"
tokio = { version = "1", features = ["full"] }
```

### Quick Start

```rust
use astrovox_sdk::{AstrovoxClient, Config};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = AstrovoxClient::new(Config {
        api_key: std::env::var("ASTROVOX_API_KEY")?,
    });

    let conversation = client
        .create_conversation(CreateConversationRequest {
            title: "My First Chat".into(),
        })
        .await?;

    let response = client
        .send_message(SendMessageRequest {
            conversation_id: conversation.id,
            message: "Hello, AI!".into(),
        })
        .await?;

    println!("{}", response.ai_message.content);

    Ok(())
}
```

---

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

## Configuration

### Environment Variables

```bash
ASTROVOX_API_KEY=your-api-key
ASTROVOX_BASE_URL=https://api.astrovox.ai/v1  # Optional, defaults to production
```

### Custom Configuration

```typescript
const client = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY,
  baseUrl: 'https://api.astrovox.ai/v1',
  timeout: 30000,
  retries: 3
})
```

```python
client = AstrovoxClient(
    api_key=os.environ["ASTROVOX_API_KEY"],
    base_url="https://api.astrovox.ai/v1",
    timeout=30,
    max_retries=3
)
```

---

## Next Steps

- Read the [API Reference](./api-reference.md)
- Explore [Examples Gallery](./examples-gallery.md)
- Check [Migration Guides](./migration-guides.md)
- Join our [Discord](https://discord.gg/astrovox) community
