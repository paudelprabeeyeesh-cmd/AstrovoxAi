# Python SDK

Official Python SDK for Astrovox AI.

## Installation

```bash
pip install astrovox
```

## Usage

```python
import astrovox

# Initialize client
client = astrovox.AstrovoxClient(
    api_key="your-api-key",
    base_url="https://api.astrovox.ai/v1"
)

# Create conversation
conversation = client.create_conversation(
    title="My Conversation",
    model="gpt-4"
)

# Send message
response = client.send_message(
    conversation_id=conversation.id,
    message="Hello, AI!"
)

print(response['ai_message']['content'])
```

## Streaming

```python
for chunk in client.stream_message(
    conversation_id=conversation.id,
    message="Write a story",
    model="gpt-4"
):
    print(chunk, end='')
```

## Error Handling

```python
from astrovox.errors import RateLimitError, AuthenticationError

try:
    response = client.send_message(conv_id, "Hello")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except AuthenticationError:
    print("Invalid API key")
```

## CLI

```bash
astrovox send <conversation_id> "Hello, AI!"
astrovox conversations
astrovox create --title "New Chat"
astrovox health
```
