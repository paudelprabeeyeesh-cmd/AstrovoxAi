# Performance Tests

## Overview

Performance tests measure latency, throughput, and resource usage under various conditions.

## Running

```bash
npm run test:perf
```

## Coverage

- Message send latency
- Streaming latency
- Concurrent request handling
- Memory usage during batch operations
- API response time distribution

## Adding New Benchmarks

Add new test cases to `performance-profiler.test.ts`.