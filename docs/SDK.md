# SDK / CLI / API / GraphQL

AstrovoxAI provides comprehensive SDKs and APIs for integrating AI capabilities into any application. This includes REST API, GraphQL, gRPC, SDKs for multiple languages, and a CLI.

## REST API

Base URL: `https://api.astrovox.ai/v1`

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/completions` | Chat completion |
| POST | `/v1/chat/stream` | Streaming chat |
| POST | `/v1/completions` | Text completion |
| GET | `/v1/models` | List available models |
| POST | `/v1/embeddings` | Generate embeddings |
| POST | `/v1/chat/agent` | Agent execution |
| POST | `/v1/vision/analyze` | Image analysis |
| POST | `/v1/audio/transcribe` | Audio transcription |
| POST | `/v1/search/semantic` | Semantic search |
| GET | `/v1/health` | Health check |

### Authentication

All requests require a Bearer token:

```bash
curl https://api.astrovox.ai/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## GraphQL

Endpoint: `https://api.astrovox.ai/v1/graphql`

### Schema

```graphql
type Query {
  conversation(id: ID!): Conversation
  conversations(first: Int, after: String): ConversationConnection
  model(id: ID!): Model
  models: [Model!]!
}

type Mutation {
  sendMessage(conversationId: ID!, content: String!): Message
  createConversation(title: String, model: String): Conversation
  deleteConversation(id: ID!): Boolean
}

type Subscription {
  messageCreated(conversationId: ID!): Message!
}

type Conversation {
  id: ID!
  title: String!
  messages(first: Int, after: String): MessageConnection!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type Message {
  id: ID!
  role: String!
  content: String!
  model: String
  createdAt: DateTime!
}
```

### Example Queries

```graphql
# Create conversation
mutation CreateConversation {
  createConversation(title: "My Chat", model: "gpt-4") {
    id
    title
  }
}

# Send message
mutation SendMessage($conversationId: ID!, $content: String!) {
  sendMessage(conversationId: $conversationId, content: $content) {
    id
    content
    role
  }
}

# Subscribe to messages
subscription OnMessage($conversationId: ID!) {
  messageCreated(conversationId: $conversationId) {
    id
    content
    role
  }
}
```

## gRPC

Proto files available in `sdk/openapi/`.

### Example

```proto
syntax = "proto3";

package astrovox.v1;

service ChatService {
  rpc Complete(CompleteRequest) returns (CompleteResponse);
  rpc Stream(StreamRequest) returns (stream StreamResponse);
}

message CompleteRequest {
  string model = 1;
  repeated Message messages = 2;
  float temperature = 3;
  int32 max_tokens = 4;
}

message Message {
  string role = 1;
  string content = 2;
}
```

```python
import grpc
from astrovox.v1 import chat_pb2, chat_pb2_grpc

channel = grpc.insecure_channel('localhost:8000')
stub = chat_pb2_grpc.ChatServiceStub(channel)

response = stub.Complete(chat_pb2.CompleteRequest(
    model="gpt-4",
    messages=[chat_pb2.Message(role="user", content="Hello!")],
    temperature=0.7,
    max_tokens=100
))
```

## Python SDK

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
from astrovox import (
    AstrovoxClient,
    AstrovoxError,
    RateLimitError,
    AuthenticationError
)

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
# Install
pip install astrovox

# Usage
astrovox send <conversation_id> "Hello, AI!"
astrovox conversations
astrovox create --title "New Chat"
astrovox health
astrovox models list
```

## TypeScript / JavaScript SDK

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

## React SDK

### Installation

```bash
npm install @astrovox/react-sdk @astrovox/sdk
```

### Usage

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

## Vue SDK

### Installation

```bash
npm install @astrovox/vue-sdk @astrovox/sdk
```

### Usage

```vue
<script setup>
import { AstrovoxChat } from '@astrovox/vue-sdk'
const apiKey = import.meta.env.VITE_ASTROVOX_API_KEY
</script>

<template>
  <AstrovoxChat :api-key="apiKey" theme="dark" />
</template>
```

## Go SDK

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

## Rust SDK

### Installation

```toml
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

```python
client = AstrovoxClient(
    api_key=os.environ["ASTROVOX_API_KEY"],
    base_url="https://api.astrovox.ai/v1",
    timeout=30,
    max_retries=3
)
```

```typescript
const client = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY,
  baseUrl: 'https://api.astrovox.ai/v1',
  timeout: 30000,
  retries: 3
})
```

## CLI Reference

```bash
# Installation
npm install -g @astrovox-ai/cli

# Chat
astrovox chat "Explain quantum computing"

# Models
astrovox models list
astrovox models info gpt-4

# Conversations
astrovox conversations
astrovox create --title "New Chat"
astrovox delete <conversation_id>

# Messages
astrovox send <conversation_id> "Hello, AI!"
astrovox stream <conversation_id> "Tell me a story"

# Embeddings
astrovox embeddings create --text "Hello world"

# Health
astrovox health
astrovox status
```

## OpenAPI Specification

Auto-generated OpenAPI spec available at:

```bash
# Generate SDKs
npm run sdk:generate
```

Supported generators:
- Python (openapi-generator)
- TypeScript/Axios
- Go
- Rust
