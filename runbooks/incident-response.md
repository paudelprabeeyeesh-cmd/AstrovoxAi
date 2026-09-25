# AstrovoxAI Incident Response Runbook

## Overview
This runbook provides procedures for responding to production incidents affecting AstrovoxAI services.

## Incident Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| P0 | Complete service outage | < 5 minutes | API down, database unavailable |
| P1 | Major degradation | < 15 minutes | Error rate > 20%, latency > 5s |
| P2 | Minor degradation | < 1 hour | Error rate 5-20%, latency 2-5s |
| P3 | Low impact | < 4 hours | Feature broken, non-critical service down |

## Incident Response Process

### 1. Detection and Alerting
Alerts are triggered by:
- Health check failures
- Error rate thresholds
- Latency thresholds
- Resource utilization (CPU, memory, disk)
- Database connectivity issues
- Queue depth (Celery)

### 2. Initial Response (First 5 Minutes)

```bash
# Acknowledge the alert
# Mark as investigating in incident management tool

# Check overall service health
curl -f https://api.astrovox.ai/health/detailed || echo "Service down"

# Check if it's a widespread issue or isolated
kubectl get pods -n production
kubectl get pods -n production --field-selector=status.phase!=Running

# Check recent deployments
gh run list --workflow=ci.yml --limit=5
```

### 3. Triage and Assessment

```bash
# Check application logs for errors
kubectl logs -l app=astrovox-backend -n production --since=30m | grep -i error | tail -50

# Check metrics
curl -s https://api.astrovox.ai/metrics | grep -E "(http_requests_total|errors|latency)"

# Check database connectivity
kubectl exec -it deployment/astrovox-backend -n production -- \
  python -c "from app.db import engine; print(engine.execute('SELECT 1').scalar())"

# Check Redis connectivity
kubectl exec -it deployment/astrovox-backend -n production -- \
  python -c "from app.redis import redis_client; redis_client.ping()"
```

### 4. Mitigation

#### Option A: Rollback (Fastest)
```bash
# Rollback to previous version
gh workflow run rollback.yml \
  -f environment=production \
  -f target_version=<PREVIOUS_VERSION> \
  -f reason="<INCIDENT_DESCRIPTION>"
```

#### Option B: Scale Up
```bash
# Scale up backend pods
kubectl scale deployment/astrovox-backend -n production --replicas=10

# Scale up frontend pods
kubectl scale deployment/astrovox-frontend -n production --replicas=5
```

#### Option C: Disable Feature Flag
```bash
# Disable problematic feature via configmap
kubectl set env deployment/astrovox-backend -n production FEATURE_ENABLE_WEBSOCKET=false

# Or via database
kubectl exec -it deployment/astrovox-backend -n production -- \
  python -c "from app.db import session; session.execute('UPDATE features SET enabled=false WHERE name=\"problematic_feature\"'); session.commit()"
```

#### Option D: Circuit Breaker
```bash
# Enable circuit breaker for external dependencies
kubectl set env deployment/astrovox-backend -n production \
  OPENAI_CIRCUIT_BREAKER=true \
  OPENAI_TIMEOUT=5
```

### 5. Communication

#### Internal Communication
```bash
# Post to Slack incident channel
curl -X POST "${{ secrets.SLACK_WEBHOOK }}" \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🚨 *P1 Incident Declared*",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*🚨 P1 Incident Declared*\n• *Service*: <service>\n• *Issue*: <description>\n• *Impact*: <impact>\n• *Incident Commander*: @<user>\n• *Status*: Investigating"
        }
      }
    ]
  }'

# Update status page (if available)
# Update incident management tool
```

#### External Communication (if needed)
```bash
# Update status page
curl -X POST "https://api.statuspage.io/v1/pages/<page>/incidents" \
  -H "Authorization: OAuth <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "incident": {
      "name": "AstrovoxAI Service Disruption",
      "status": "investigating",
      "body": "We are currently investigating an issue with our service.",
      "components": [{"name": "API", "status": "degraded"}]
    }
  }'
```

### 6. Resolution and Recovery

```bash
# After fix is deployed, verify recovery
curl -f https://api.astrovox.ai/health/detailed || echo "Still down"

# Monitor metrics for 15 minutes
watch -n 30 'curl -s https://api.astrovox.ai/metrics | grep http_requests_total'

# If recovered, mark incident as resolved
gh issue close <issue-number> --comment "Resolved: <resolution>"
```

### 7. Post-Incident Review

Create a post-incident review document:

```markdown
## Incident Summary
- **Incident ID**: INC-2024-001
- **Severity**: P1
- **Duration**: 45 minutes
- **Start Time**: 2024-01-15 14:30 UTC
- **End Time**: 2024-01-15 15:15 UTC
- **Impact**: 5000 users affected

## Timeline
- 14:30 - Alert triggered
- 14:32 - On-call engineer acknowledged
- 14:35 - Root cause identified
- 14:40 - Rollback initiated
- 14:45 - Rollback completed
- 15:00 - Monitoring for 15 minutes
- 15:15 - Incident resolved

## Root Cause
Database connection pool exhaustion due to connection leak in new code.

## Remediation
- Rolled back to previous version
- Applied hotfix for connection leak
- Added connection pool monitoring

## Action Items
- [ ] Add connection pool monitoring alerts
- [ ] Add integration test for connection pool exhaustion
- [ ] Update runbook with connection pool troubleshooting
- [ ] Schedule blameless post-mortem
```

## Common Incident Scenarios

### Scenario 1: Database Connection Exhaustion
```bash
# Symptoms: 500 errors, timeout errors
# Check: Connection pool status
kubectl exec -it deployment/astrovox-backend -n production -- \
  python -c "from app.db import engine; print(engine.pool.checkedin())"

# Mitigation: Restart pods
kubectl rollout restart deployment/astrovox-backend -n production

# Permanent fix: Increase pool size, fix connection leaks
```

### Scenario 2: Redis Connection Issues
```bash
# Symptoms: Cache misses, session errors
# Check: Redis connectivity
kubectl exec -it deployment/astrovox-backend -n production -- redis-cli ping

# Mitigation: Restart Redis
kubectl rollout restart statefulset/redis -n production

# Check Redis logs
kubectl logs -l app=redis -n production --tail=100
```

### Scenario 3: High Memory Usage
```bash
# Symptoms: OOMKilled pods, slow responses
# Check: Pod resource usage
kubectl top pods -n production

# Mitigation: Increase memory limits
kubectl set resources deployment/astrovox-backend -n production \
  --limits=memory=4Gi --requests=memory=1Gi

# Restart pods
kubectl rollout restart deployment/astrovox-backend -n production
```

### Scenario 4: Disk Space Full
```bash
# Symptoms: Write failures, pod crashes
# Check: Disk usage
kubectl exec -it <pod> -n production -- df -h

# Mitigation: Clean up logs
kubectl exec -it <pod> -n production -- \
  sh -c "find /app/logs -name '*.log' -mtime +7 -delete"

# Increase persistent volume
kubectl patch pvc <pvc-name> -n production -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'
```

## Emergency Contacts
- **PagerDuty/On-Call**: Check on-call schedule
- **DevOps Lead**: @devops-lead
- **Engineering Manager**: @eng-manager
- **Security Team**: @security-team
