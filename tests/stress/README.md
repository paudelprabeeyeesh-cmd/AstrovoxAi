# Stress Tests

## Overview

Stress tests push the system beyond normal operating conditions to identify breaking points and failure modes.

## Running

```bash
npm run test:stress
```

## Scenarios

- `sustained` - 100 VUs for 2 minutes
- `stress` - Ramps from 10 to 1000 VUs over 2 minutes

## Thresholds

- `p(99) < 2000ms` response time under stress
- `error rate < 5%`

## Environment

Set `BASE_URL` and `AUTH_TOKEN`:

```bash
k6 run -e BASE_URL=http://localhost:8000 -e AUTH_TOKEN=token tests/stress/chat-stress-test.js
```