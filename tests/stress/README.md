# Stress Tests

Stress tests evaluate system behavior under extreme load.

## Running Stress Tests

```bash
npm run test:stress
```

## Scenarios

### Scenario 1: Extreme Concurrency
- 1000 concurrent users
- Duration: 5 minutes
- Expected: Service remains available

### Scenario 2: Rapid Fire Requests
- 10,000 requests/minute
- Duration: 2 minutes
- Expected: Rate limiting kicks in appropriately

### Scenario 3: Large Payloads
- 100KB message payloads
- 500 concurrent requests
- Expected: No crashes, reasonable latency

## Results Interpretation

- P95 latency < 2000ms: PASS
- Error rate < 5%: PASS
- No memory leaks: PASS
