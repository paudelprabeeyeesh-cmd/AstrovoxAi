# Troubleshooting Guide

## Backend Issues

### Service won't start

**Symptoms:** `uvicorn` exits immediately or `/health` returns 503.

**Diagnosis:**
```bash
# Check logs
docker compose logs backend

# Verify env vars
docker compose exec backend env | grep -E 'DATABASE_URL|REDIS_URL|SECRET_KEY'

# Test DB connectivity
docker compose exec backend python -c "import asyncpg; print('DB OK')"
docker compose exec backend python -c "import redis; print('Redis OK')"
```

**Fix:**
- Ensure `DATABASE_URL` uses `postgresql://` not `postgres://`
- Ensure `SECRET_KEY` is at least 32 characters
- Restart: `docker compose restart backend`

### Import errors in main.py

**Symptoms:** `ImportError: cannot import name 'X' from 'app.Y'`

**Diagnosis:**
```bash
python -c "from app.main import app"
```

**Fix:**
- Ensure all relative imports use `from .module import X`
- Check for circular imports between routers

### Database connection pool exhausted

**Symptoms:** `too many connections for role "astrovox"`

**Diagnosis:**
```sql
SELECT count(*) FROM pg_stat_activity WHERE datname = 'astrovox';
```

**Fix:**
- Reduce `max_connections` in PostgreSQL config
- Add connection pooling (PgBouncer)
- Fix connection leaks (ensure `client.close()` is called)

### Slow API responses

**Symptoms:** p99 latency > 2s

**Diagnosis:**
```bash
curl -w "\n" -o /dev/null -s http://localhost:8000/health
curl http://localhost:8000/metrics | grep http_request_duration_seconds
```

**Fix:**
- Check for missing DB indexes
- Enable Redis caching for hot endpoints
- Review LLM provider latency

## Frontend Issues

### Blank page / white screen

**Diagnosis:**
```bash
# Check browser console for JS errors
# Check network tab for failed API calls
```

**Fix:**
- Verify `VITE_API_URL` is set correctly
- Check CORS configuration in backend
- Run `npm run build` and inspect for errors

### 401 on every request

**Symptoms:** Logged in but all API calls return 401.

**Fix:**
- Clear cookies and re-login
- Verify `Authorization` header format: `Bearer <token>`
- Check token expiry (default: 30 minutes)

### Chat streaming stops mid-response

**Symptoms:** SSE stream closes unexpectedly.

**Fix:**
- Check nginx proxy timeout settings (default: 60s)
- Increase `proxy_read_timeout` to `300s`
- Verify backend is not rate-limiting

## Database Issues

### Migration fails

**Symptoms:** `alembic upgrade head` errors.

**Fix:**
```bash
# Check current revision
alembic current

# Stamp if needed
alembic stamp head

# Re-run
alembic upgrade head
```

### pgvector extension missing

**Symptoms:** `ERROR: extension "vector" does not exist`

**Fix:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Infrastructure Issues

### Pod CrashLoopBackOff

**Diagnosis:**
```bash
kubectl describe pod <pod> -n astrovox
kubectl logs <pod> -n astrovox --tail=200 --previous
```

**Common causes:**
- OOMKilled: increase memory limits
- CrashLoop: check app startup logs
- ImagePullBackOff: verify image exists and pull secret

### Ingress returning 502/503

**Fix:**
```bash
kubectl get pods -n astrovox
kubectl describe ingress astrovox-ingress -n astrovox
kubectl get events -n astrovox --sort-by='.lastTimestamp'
```

### Redis full / OOM

**Diagnosis:**
```bash
kubectl exec -it <redis-pod> -n astrovox -- redis-cli info memory
```

**Fix:**
- Increase `maxmemory` in deployment
- Review cache TTLs
- Consider Redis Cluster for > 4GB

## Performance

### High CPU usage

**Diagnosis:**
```bash
kubectl top pods -n astrovox
kubectl exec -it <pod> -n astrovox -- ps aux
```

**Fix:**
- Profile with `py-spy` or `cProfile`
- Check for infinite loops or recursive LLM calls
- Scale horizontally with HPA

### Memory leak

**Diagnosis:**
```bash
kubectl top pods -n astrovox --containers
```

**Fix:**
- Profile with `memray` or `tracemalloc`
- Check for unbounded lists/dicts
- Verify connections are closed

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Missing/invalid token | Re-login or refresh token |
| `403 Forbidden` | Email not verified | Check email for verification link |
| `404 Not Found` | Wrong ID or deleted | Verify resource exists |
| `422 Unprocessable` | Invalid request body | Check field constraints in schema |
| `429 Too Many Requests` | Rate limited | Wait or increase `RATE_LIMIT` |
| `500 Internal Server` | Server error | Check logs for stack trace |
| `503 Service Unavailable` | Backend down | Restart deployment |

## Getting Help

1. Check [FAQ](./faq.md)
2. Search [GitHub Issues](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/issues)
3. Ask in [Discord](https://discord.gg/astrovox)
4. Open a new issue with logs and reproduction steps
