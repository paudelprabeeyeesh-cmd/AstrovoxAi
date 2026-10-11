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
# AstrovoxAI SDK

Python and TypeScript snippets for integrating with the AstrovoxAI API.

## Base URL

```
http://localhost:8000
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
Install dependencies:
```bash
pip install httpx pydantic
```

### Client Setup

```python
from typing import Optional
import httpx


class AstrovoxClient:
    def __init__(self, base_url: str = "http://localhost:8000", access_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.client = httpx.Client(timeout=30.0)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def health(self) -> dict:
        resp = self.client.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def login(self, email: str, password: str) -> dict:
        resp = self.client.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        return resp.json()

    def create_conversation(self, title: str, model: str = "gpt-4") -> dict:
        resp = self.client.post(
            f"{self.base_url}/chat/conversations",
            json={"title": title, "model": model},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def send_message(self, conversation_id: int, message: str, model: str = "gpt-4") -> dict:
        resp = self.client.post(
            f"{self.base_url}/chat/message",
            json={
                "conversation_id": conversation_id,
                "message": message,
                "model": model,
            },
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def save_memory(self, content: str, importance: int = 1) -> dict:
        resp = self.client.post(
            f"{self.base_url}/memory/save",
            json={"content": content, "importance": importance},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self.client.close()
```

### Usage Example

```python
client = AstrovoxClient()

# Health check
print(client.health())

# Login
login_resp = client.login("user@example.com", "secure_password")
access_token = login_resp["session"]["access_token"]
client.access_token = access_token

# Create conversation
conv = client.create_conversation("My Chat", "gpt-4")
conversation_id = conv["conversation"]["id"]

# Send message
msg = client.send_message(conversation_id, "Hello, how are you?")
print(msg["ai_message"]["content"])

# Save memory
client.save_memory("User prefers concise responses", importance=2)

client.close()
```

### Async Usage

```python
import asyncio
import httpx


async def async_example():
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get("http://localhost:8000/health")
        print(resp.json())

        resp = await client.post(
            "http://localhost:8000/auth/login",
            json={"email": "user@example.com", "password": "secure_password"},
        )
        print(resp.json())


asyncio.run(async_example())
```

## TypeScript SDK

Install dependencies:
```bash
npm install axios
```

### Client Setup

```typescript
interface AstrovoxConfig {
  baseUrl?: string;
  accessToken?: string;
}

interface LoginResponse {
  status: string;
  message: string;
  user: { id: string; email: string };
  session: { access_token: string; refresh_token: string };
}

interface Conversation {
  id: number;
  user_id: string;
  title: string;
  model: string;
  created_at: string;
  updated_at: string;
}

interface Message {
  id: number;
  conversation_id: number;
  role: string;
  content: string;
  created_at: string;
}

class AstrovoxClient {
  private baseUrl: string;
  private accessToken?: string;

  constructor(config: AstrovoxConfig = {}) {
    this.baseUrl = (config.baseUrl || "http://localhost:8000").replace(/\/$/, "");
    this.accessToken = config.accessToken;
  }

  private headers(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }
    return headers;
  }

  async health() {
    const resp = await fetch(`${this.baseUrl}/health`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  async login(email: string, password: string): Promise<LoginResponse> {
    const resp = await fetch(`${this.baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  async createConversation(title: string, model: string = "gpt-4"): Promise<Conversation> {
    const resp = await fetch(`${this.baseUrl}/chat/conversations`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ title, model }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    return data.conversation;
  }

  async sendMessage(conversationId: number, message: string, model: string = "gpt-4"): Promise<Message> {
    const resp = await fetch(`${this.baseUrl}/chat/message`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ conversation_id: conversationId, message, model }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    return data.ai_message;
  }

  async saveMemory(content: string, importance: number = 1) {
    const resp = await fetch(`${this.baseUrl}/memory/save`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ content, importance }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  setAccessToken(token: string) {
    this.accessToken = token;
  }
}
```

### Usage Example

```typescript
const client = new AstrovoxClient();

// Health check
const health = await client.health();
console.log(health);

// Login
const loginResp = await client.login("user@example.com", "secure_password");
client.setAccessToken(loginResp.session.access_token);

// Create conversation
const conv = await client.createConversation("My Chat", "gpt-4");
const conversationId = conv.id;

// Send message
const aiMsg = await client.sendMessage(conversationId, "Hello, how are you?");
console.log(aiMsg.content);

// Save memory
await client.saveMemory("User prefers concise responses", 2);
```

### React Hook Example

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

function useAstrovox() {
  const queryClient = useQueryClient();
  const client = new AstrovoxClient({ accessToken: "user-token" });

  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => client.health(),
  });

  const sendMessage = useMutation({
    mutationFn: ({ conversationId, message }: { conversationId: number; message: string }) =>
      client.sendMessage(conversationId, message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["messages"] });
    },
  });

  return { health, sendMessage };
}
```

## Error Handling

Both SDKs raise on non-2xx responses. Wrap calls in `try/catch` (Python) or `try/catch` (TypeScript).

```python
try:
    client.login(email, password)
except httpx.HTTPStatusError as e:
    print(f"Request failed: {e.response.status_code} - {e.response.text}")
```

```typescript
try {
    await client.login(email, password);
} catch (e) {
    console.error(`Request failed: ${(e as Error).message}`);
}
```
