# E2E Tests

## Overview

End-to-end tests verify complete user workflows through the browser.

## Running

```bash
npm run test:e2e
```

## Test Files

- `chat.spec.js` - Core chat flows
- `navigation.spec.js` - Navigation and routing
- `advanced-flows.spec.js` - Edit, delete, error states
- `auth.spec.js` - Authentication flows
- `themes.test.js` - Theme switching (visual regression)

## CI

Run in CI with:

```bash
npx playwright test --project=chromium
```