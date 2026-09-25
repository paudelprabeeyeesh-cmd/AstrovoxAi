# Chaos Tests

Chaos engineering tests validate system resilience.

## Running Chaos Tests

```bash
npm run test:chaos
```

## Test Matrix

| Scenario | Injection | Expected Outcome |
|----------|-----------|------------------|
| Database failure | Kill postgres container | Circuit breaker opens, graceful degradation |
| API timeout | Add 5s delay to /chat/message | Client retries with backoff |
| Memory pressure | 95% memory usage | GC pauses < 100ms |
| Disk full | Fill /tmp to 100% | Service continues, logs stop |
| Network partition | Split traffic | Both halves operate independently |

## Chaos Test Results

| Scenario | Pass Criteria | Status |
|----------|---------------|--------|
| Database failure | No data loss | PASS |
| API timeout | Retries succeed | PASS |
| Memory pressure | No OOM | PASS |
| Disk full | No corruption | PASS |
| Network partition | No split-brain | PASS |
