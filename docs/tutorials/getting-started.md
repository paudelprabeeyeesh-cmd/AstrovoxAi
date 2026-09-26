# Getting Started Tutorial

This tutorial walks you through your first AstrovoxAI integration.

## Prerequisites

- An AstrovoxAI account and API key
- Python 3.9+ or Node.js 18+

## Step 1: Install the SDK

```bash
# Python
pip install astrovox

# TypeScript
npm install @astrovox/sdk
```

## Step 2: Initialize the Client

```python
import astrovox

client = astrovox.AstrovoxClient(api_key="your-api-key")
```

## Step 3: Create a Conversation

```python
conversation = client.create_conversation(title="My First Chat")
print(f"Conversation ID: {conversation.id}")
```

## Step 4: Send a Message

```python
response = client.send_message(conversation.id, "Hello, AstrovoxAI!")
print(response["ai_message"]["content"])
```

## Next Steps

- Explore the [API Reference](../docs/API.md)
- Try the [API Playground](../docs/API_PLAYGROUND.md)
- Read the [Architecture Docs](../docs/ARCHITECTURE.md)
