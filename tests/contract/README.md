# Contract Tests

## Overview

API contract tests verify that the client SDK and backend API agree on request/response shapes.

## Running

```bash
npm run test:contract
```

## Coverage

- `sendMessage` - POST /chat/message
- `createConversation` - POST /conversations
- `listConversations` - GET /conversations
- Error handling - 401, 429 responses

## Adding New Contracts

1. Add a new `it` block in `api-contract.test.ts`
2. Mock `global.fetch` with the expected response shape
3. Assert request shape and response schema