# AstrovoxAI SDK

Python and TypeScript snippets for integrating with the AstrovoxAI API.

## Base URL

```
http://localhost:8000
```

## Python SDK

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
