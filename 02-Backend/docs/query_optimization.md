# Database Query Optimization Notes

## Indexes
- `memories(user_id, memory_type, created_at)`
- `usage(user_id, created_at)`
- `conversations(user_id, created_at)`
- `messages(conversation_id, created_at)`
- `documents(user_id, created_at)`

## Query Patterns
- Always filter by `user_id` first for tenant isolation
- Use covering indexes for frequent list endpoints
- Avoid `SELECT *`; fetch only required columns
- Use cursor-based pagination for large result sets

## Connection Pooling
- Current: min=2, max=10
- Recommended: min=10, max=50 for production
- Consider `NullPool` with per-request connections for async FastAPI

## Query Examples

### Before
```sql
SELECT * FROM memories WHERE user_id = ? ORDER BY created_at DESC
```

### After
```sql
SELECT id, key, value, memory_type, created_at
FROM memories
WHERE user_id = ?
ORDER BY created_at DESC
LIMIT 50
```

## Maintenance
- Run `ANALYZE` after bulk imports
- Monitor slow queries via Prometheus
- Archive old records to cold storage
