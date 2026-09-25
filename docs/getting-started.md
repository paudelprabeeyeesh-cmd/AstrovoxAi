# Getting Started with Astrovox AI

Welcome to Astrovox AI! This guide will help you get up and running in minutes.

## Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/astrovox/astrovox.git
cd astrovox

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env

# Run development server
npm run dev
```

### Using the SDK

```python
import astrovox

client = astrovox.AstrovoxClient(api_key="your-api-key")
conversation = client.create_conversation(title="My First Chat")
response = client.send_message(conversation.id, "Hello, AI!")
print(response['ai_message']['content'])
```

```typescript
import { AstrovoxClient } from '@astrovox/sdk'

const client = new AstrovoxClient({ apiKey: 'your-api-key' })
const conversation = await client.createConversation({ title: 'My First Chat' })
const response = await client.sendMessage({ conversationId: conversation.id, message: 'Hello, AI!' })
console.log(response.ai_message.content)
```

## First Conversation

1. Open your browser to `http://localhost:5173`
2. Sign up or log in
3. Click "New Chat" to start a conversation
4. Type your first message and press Enter

## Features

- Multi-chat tabs for parallel conversations
- Chat branching to explore different responses
- Markdown, KaTeX, and Mermaid rendering
- Voice input and output
- File uploads and drag-and-drop
- Camera capture and screen sharing
- Team workspaces and shared conversations
- Keyboard-first navigation
- Full WCAG 2.2 AA accessibility

## Next Steps

- Read the [API Reference](./api-reference.md)
- Check out [Tutorials](./tutorials.md)
- Explore [Examples](./examples.md)
- Join our [Discord](https://discord.gg/astrovox)

## Support

- [GitHub Issues](https://github.com/astrovox/astrovox/issues)
- [Documentation](./)
- [Community Forum](https://github.com/astrovox/astrovox/discussions)
