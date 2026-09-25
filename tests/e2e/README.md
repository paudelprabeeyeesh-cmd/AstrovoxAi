# Playwright Configuration

E2E tests use Playwright.

## Setup

```bash
npm init playwright@latest
npx playwright install
```

## Config

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

## Running Tests

```bash
# All E2E tests
npm run test:e2e

# Specific browser
npx playwright test --project=chromium

# Headed mode
npx playwright test --headed

# Debug mode
npx playwright test --debug
```

## Accessibility Tests

```bash
npm run test:accessibility
```

Uses `@axe-core/playwright` for automated accessibility testing.
