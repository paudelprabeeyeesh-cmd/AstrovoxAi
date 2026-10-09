# Runbook: Responding to Alerts

## High Error Rate (5xx > 5%)

### Symptoms
- Grafana dashboard shows spike in 5xx responses
- Prometheus alert: `HighErrorRate`
- Sentry error volume increases

### Investigation
1. Check recent deployments in Kubernetes:
   ```bash
   kubectl rollout history deployment/astrovox-backend -n astrovox
   kubectl describe deployment astrovox-backend -n astrovox
   ```
2. Review application logs:
   ```bash
   kubectl logs -l app=astrovox-backend -n astrovox --tail=100
   ```
3. Check database connectivity:
   ```bash
   kubectl exec -it <pod> -n astrovox -- pg_isready -U astrovox
   ```
4. Verify Redis connectivity:
   ```bash
   kubectl exec -it <pod> -n astrovox -- redis-cli -h redis-master ping
   ```
5. Check external API status (OpenAI, Anthropic, etc.)

### Resolution
- Rollback if recent deployment:
  ```bash
  kubectl rollout undo deployment/astrovox-backend -n astrovox
  ```
- Restart pods if database/redis issues:
  ```bash
  kubectl rollout restart deployment/astrovox-backend -n astrovox
  ```
- Scale up if overloaded:
  ```bash
  kubectl scale deployment/astrovox-backend -n astrovox --replicas=5
  ```

---

## Slow Responses (P95 > 2s)

### Symptoms
- Grafana shows latency spike
- Prometheus alert: `SlowResponses`
- User complaints about slowness

### Investigation
1. Check database query performance:
   ```bash
   kubectl exec -it <postgres-pod> -n astrovox -- psql -U astrovox -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
   ```
2. Review slow query log
3. Check Redis hit rate
4. Verify external API latency (OpenAI, etc.)

### Resolution
- Tune database queries (see `query_optimization.md`)
- Increase connection pool size
- Enable query caching in Redis
- Consider scaling horizontally

---

## Memory Leak / OOM

### Symptoms
- Prometheus alert: `HighMemoryUsage`
- Pods being OOMKilled
- Increasing RSS over time

### Investigation
1. Check pod status:
   ```bash
   kubectl get pods -n astrovox -o wide
   kubectl describe pod <pod-name> -n astrovox | grep -A 10 "Last State"
   ```
2. Profile memory:
   ```bash
   kubectl exec -it <pod> -n astrovox -- python -m memory_profiler app/main.py
   ```

### Resolution
- Restart affected pods:
  ```bash
  kubectl rollout restart deployment/astrovox-backend -n astrovox
  ```
- Fix memory leak in code
- Increase memory limits temporarily

---

## Redis Outage

### Symptoms
- Prometheus alert: `RedisDown`
- Cache misses spike
- Rate limiting fails

### Investigation
1. Check Redis pod status:
   ```bash
   kubectl get pods -l app=redis-master -n astrovox
   kubectl logs -l app=redis-master -n astrovox --tail=50
   ```
2. Verify Redis connectivity:
   ```bash
   kubectl exec -it <backend-pod> -n astrovox -- redis-cli -h redis-master ping
   ```

### Resolution
- Restart Redis:
  ```bash
  kubectl rollout restart statefulset/redis-master -n astrovox
  ```
- Clear stale keys if needed:
  ```bash
  kubectl exec -it <redis-pod> -n astrovox -- redis-cli FLUSHDB
  ```

---

## Database Connection Exhaustion

### Symptoms
- `OperationalError: connection pool exhausted`
- Slow API responses
- Database CPU at 100%

### Investigation
1. Check active connections:
   ```bash
   kubectl exec -it <postgres-pod> -n astrovox -- psql -U astrovox -c "SELECT count(*) FROM pg_stat_activity;"
   ```
2. Review connection pool configuration
3. Check for long-running queries

### Resolution
- Increase pool size in `database.py`
- Kill idle connections:
  ```sql
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < now() - interval '5 minutes';
  ```
- Restart backend pods to release connections

---

## Kubernetes Pod Issues

### Symptoms
- Pods not starting
- CrashLoopBackOff
- ImagePullBackOff

### Investigation
1. Describe pod:
   ```bash
   kubectl describe pod <pod-name> -n astrovox
   ```
2. Check events:
   ```bash
   kubectl get events -n astrovox --sort-by='.lastTimestamp'
   ```

### Resolution
- Check image pull secrets
- Verify resource availability
- Check for security context issues
- Review pod security policies
