# Chaos Engineering Tests

## Overview

Chaos tests verify that the system degrades gracefully under failure conditions.

## Running

```bash
npm run test:chaos
```

## Coverage

- Database outage handling
- Network partition resilience
- Retry behavior on transient failures
- Circuit breaker behavior
- Graceful fallback when dependencies fail
- Memory pressure handling

## Adding New Scenarios

Add new test cases to `chaos.test.ts` using the `ChaosFaultInjector` helper.