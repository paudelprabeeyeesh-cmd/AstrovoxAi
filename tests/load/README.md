# Load Tests

Load tests verify system performance under expected traffic.

## Running Load Tests

```bash
npm run test:load
```

## Configuration

Set environment variables:

```bash
export BASE_URL=https://api.astrovox.ai
export AUTH_TOKEN=your-token
k6 run tests/load/chat-load-test.js
```

## Test Scenarios

### Ramp-up Test
- 0 to 50 VUs over 30 seconds
- Hold 50 VUs for 1 minute
- Ramp down to 0

### Spike Test
- Sudden spike to 200 VUs
- Verify auto-scaling kicks in
- Measure recovery time

## Success Criteria

- P95 latency < 500ms
- Error rate < 1%
- No timeouts
