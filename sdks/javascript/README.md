# AstrovoxAI JavaScript SDK

Official JavaScript/TypeScript SDK for AstrovoxAI.

## Installation

```bash
npm install @astrovox/sdk
```

## Quick Start

```typescript
import { AstrovoxClient } from '@astrovox/sdk'

const client = new AstrovoxClient('avx_...')
const conversation = await client.createConversation({ title: 'My Chat' })
const response = await client.sendMessage(conversation.id, 'Hello, Astrovox!')
console.log(response)
```

See [sdk/typescript/](../sdk/typescript/) for the full source code and [TypeScript SDK Guide](/sdk/typescript) for documentation.
