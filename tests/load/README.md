# Load Tests

## Overview

Load tests verify that the system handles expected traffic volumes within performance thresholds.

## Running

```bash
npm run test:load
```

## Scenarios

- `smoke` - 1 VU for 10s, validates basic health and chat endpoints
- `ramp` - Ramps from 0 to 100 VUs over 2 minutes
- `spike` - Ramps to 500 VUs in 10s, then ramps down

## Thresholds

- `p(95) < 500ms` response time
- `p(99) < 1000ms` response time
- `error rate < 1%`

## Environment

Set `BASE_URL` and `AUTH_TOKEN`:

```bash
k6 run -e BASE_URL=http://localhost:8000 -e AUTH_TOKEN=token tests/load/chat-load-test.js
```