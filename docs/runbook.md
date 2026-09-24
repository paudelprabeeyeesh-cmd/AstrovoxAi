# Incident Runbook

## Service Down

### Symptoms
- `/health` returns 503 or times out
- Pods in CrashLoopBackOff or ImagePullBackOff
- Ingress returns 502/503

### Diagnosis

```bash
# Check pod status
kubectl get pods -n astrovox

# Describe failing pod
kubectl describe pod <pod-name> -n astrovox

# Check events
kubectl get events -n astrovox --sort-by='.lastTimestamp'

# Check recent logs
kubectl logs <pod-name> -n astrovox --tail=200

# Check previous container logs (if crashed)
kubectl logs <pod-name> -n astrovox --tail=200 --previous
```

### Remediation

```bash
# Restart deployment
kubectl rollout restart deployment/astrovox-backend -n astrovox

# If image issue, force pull
kubectl set image deployment/astrovox-backend backend=astrovox-backend:latest -n astrovox

# Scale down/up if stuck
kubectl scale deployment/astrovox-backend --replicas=0 -n astrovox
kubectl scale deployment/astrovox-backend --replicas=3 -n astrovox
```

## High Error Rate

### Symptoms
- Alertmanager: `HighErrorRate`
- 5xx responses >5% over 5 minutes

### Diagnosis

```bash
# Check metrics
curl https://api.astrovox.ai/metrics | grep http_requests_total

# Check application logs
kubectl logs -l app=astrovox-backend -n astrovox --tail=500 | grep -i error

# Check database connectivity
kubectl exec -it <pod-name> -n astrovox -- python -c "import asyncpg; print('DB OK')"

# Check Redis connectivity
kubectl exec -it <pod-name> -n astrovox -- python -c "import redis; print('Redis OK')"
```

### Remediation

```bash
# Rollback to previous version
kubectl rollout undo deployment/astrovox-backend -n astrovox

# Scale up to handle load
kubectl scale deployment/astrovox-backend --replicas=5 -n astrovox

# Check rate limiting
kubectl logs -l app=astrovox-backend -n astrovox | grep -i "rate limit"
```

## High Memory Usage

### Symptoms
- Alertmanager: `HighMemoryUsage`
- Pods being OOMKilled

### Diagnosis

```bash
# Check current memory usage
kubectl top pods -n astrovox

# Check for memory leaks in logs
kubectl logs -l app=astrovox-backend -n astrovox | grep -i memory

# Check HPA status
kubectl get hpa -n astrovox
```

### Remediation

```bash
# Increase memory limits
kubectl patch deployment astrovox-backend -n astrovox -p '{"spec":{"template":{"spec":{"containers":[{"name":"backend","resources":{"limits":{"memory":"1Gi"}}}]}}}}'

# Scale horizontally
kubectl scale deployment/astrovox-backend --replicas=5 -n astrovox
```

## Database Down

### Symptoms
- Alertmanager: `DatabaseDown`
- Connection errors in application logs

### Diagnosis

```bash
# Check postgres pod
kubectl get pods -l app=postgres -n astrovox

# Check postgres logs
kubectl logs -l app=postgres -n astrovox --tail=200

# Check PVC status
kubectl get pvc -n astrovox
```

### Remediation

```bash
# Restart postgres
kubectl rollout restart statefulset/postgres -n astrovox

# If data corruption, restore from backup
kubectl exec -it <postgres-pod> -n astrovox -- psql -U astrovox -c "SELECT pg_reload_conf();"

# Verify connectivity from backend
kubectl exec -it <backend-pod> -n astrovox -- python -c "
import asyncpg
asyncpg.connect('postgresql://astrovox:astrovox@postgres:5432/astrovox')
"
```

## Redis Down

### Symptoms
- Alertmanager: `RedisDown`
- Cache misses increasing, rate limiting not working

### Diagnosis

```bash
# Check redis pod
kubectl get pods -l app=redis-master -n astrovox

# Ping redis
kubectl exec -it <redis-pod> -n astrovox -- redis-cli ping

# Check memory usage
kubectl exec -it <redis-pod> -n astrovox -- redis-cli info memory
```

### Remediation

```bash
# Restart redis
kubectl rollout restart statefulset/redis-master -n astrovox

# Clear cache if corrupted
kubectl exec -it <redis-pod> -n astrovox -- redis-cli FLUSHDB
```

## Pod CrashLooping

### Symptoms
- Alertmanager: `PodCrashLooping`
- Restarts >0 over 15 minutes

### Diagnosis

```bash
# Check restart count
kubectl get pods -n astrovox

# Get crash details
kubectl logs <pod-name> -n astrovox --tail=200 --previous
kubectl describe pod <pod-name> -n astrovox | grep -A 20 "Last State"
```

### Remediation

```bash
# Check for resource constraints
kubectl describe pod <pod-name> -n astrovox | grep -A 5 "Limits"

# Increase resources if OOMKilled
kubectl patch deployment astrovox-backend -n astrovox -p '{"spec":{"template":{"spec":{"containers":[{"name":"backend","resources":{"limits":{"memory":"1Gi"}}}]}}}}'

# Rollout restart
kubectl rollout restart deployment/astrovox-backend -n astrovox
```

## Post-Mortem Template

After resolving incident:

1. **Timeline**: When did it start, when detected, when resolved
2. **Impact**: Users affected, services impacted
3. **Root Cause**: What caused the issue
4. **Resolution**: Steps taken to resolve
5. **Action Items**: Preventive measures to implement
