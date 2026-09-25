# Tests Overview

## Test Structure

```
tests/
├── unit/                    # Unit tests (Vitest)
│   ├── components/         # Component tests
│   ├── hooks/             # Hook tests
│   └── design/            # Design system tests
├── integration/            # Integration tests
│   └── components/         # Component integration tests
├── e2e/                    # End-to-end tests (Playwright)
│   ├── chat.spec.js
│   └── navigation.spec.js
├── security/               # Security tests
│   └── auth.test.ts
├── load/                   # Load tests (k6)
│   ├── chat-load-test.js
│   └── README.md
├── stress/                 # Stress tests (k6)
│   ├── chat-stress-test.js
│   └── README.md
├── chaos/                  # Chaos tests
│   ├── chat-chaos-test.md
│   └── README.md
├── contract/               # Contract tests
│   ├── api-contract.test.ts
│   └── README.md
├── snapshot/               # Snapshot tests
│   └── README.md
├── visual-regression/      # Visual regression tests
│   ├── appearance.test.js
│   └── README.md
├── ai-evals/               # AI quality evaluations
│   ├── model-quality.test.ts
│   └── model-quality.eval.md
├── redteam/                # Red team security tests
│   ├── prompt-injection.test.md
│   └── README.md
├── performance/            # Performance benchmarks
│   ├── benchmark.test.md
│   └── README.md
└── accessibility/          # Accessibility tests
    └── a11y.test.js
```

## Running All Tests

```bash
# Unit tests
npm run test:unit

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e

# Security tests
npm run test:security

# Load tests
npm run test:load

# Stress tests
npm run test:stress

# Chaos tests
npm run test:chaos

# Contract tests
npm run test:contract

# Visual regression
npm run test:visual

# AI evals
npm run test:ai-eval

# Red team
npm run test:redteam

# Performance
npm run test:perf

# Accessibility
npm run test:accessibility

# All tests
npm test
```
