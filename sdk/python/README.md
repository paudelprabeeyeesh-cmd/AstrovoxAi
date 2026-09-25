# Python SDK

Official Python SDK for Astrovox AI.

## Installation

```bash
pip install astrovox
```

## Quick Start

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

## Advanced Usage

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

## Error Handling

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

## CLI

```bash
astrovox send <conversation_id> "Hello, AI!"
astrovox conversations
astrovox create --title "New Chat"
astrovox health
```

## Configuration

```python
client = AstrovoxClient(
    api_key=os.environ["ASTROVOX_API_KEY"],
    base_url="https://api.astrovox.ai/v1",
    timeout=30,
    max_retries=3
)
```
