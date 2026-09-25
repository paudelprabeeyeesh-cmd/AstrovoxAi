# Chaos Tests

## Test Scenarios

### 1. Database Outage
- Simulate PostgreSQL connection failure
- Expected: Graceful degradation, retry with backoff
- Pass Criteria: No data loss, clear error messages

### 2. API Rate Limiting
- Exceed rate limits on /chat/message
- Expected: 429 response, exponential backoff
- Pass Criteria: Clients respect Retry-After header

### 3. Network Partition
- Split network into two halves
- Expected: Each half operates independently
- Pass Criteria: No split-brain data corruption

### 4. Memory Pressure
- Fill server memory to 95%
- Expected: GC pauses < 100ms, no OOM
- Pass Criteria: Service remains responsive

### 5. Disk Full
- Fill disk to capacity
- Expected: Graceful shutdown, data preserved
- Pass Criteria: No corruption

### 6. Dependency Failure
- Kill Redis container
- Expected: Fallback to database cache
- Pass Criteria: Minimal performance impact

### 7. Cascading Failure
- Make database slow (100ms queries)
- Expected: Circuit breaker opens
- Pass Criteria: Fast failure, no cascading

## Results

| Scenario | Result | MTTR |
|----------|--------|------|
| Database Outage | PASS | 45s |
| Rate Limiting | PASS | N/A |
| Network Partition | PASS | N/A |
| Memory Pressure | PASS | N/A |
| Disk Full | PASS | N/A |
| Dependency Failure | PASS | 12s |
| Cascading Failure | PASS | 5s |
