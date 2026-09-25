# Integration Tests

## Overview

Integration tests verify that multiple modules work together correctly.

## Running

```bash
npm run test:integration
```

## Test Files

- `api-integration.test.ts` - API client integration
- `auth.integration.test.ts` - Authentication flow
- `websocket.integration.test.ts` - WebSocket communication
- `slo.integration.test.ts` - SLO validation
- `error-budget.integration.test.ts` - Error budget tracking
- `components/` - Component integration tests

## Adding New Tests

Add new test files to `tests/integration/`.