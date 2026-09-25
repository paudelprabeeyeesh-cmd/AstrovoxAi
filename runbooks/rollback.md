# AstrovoxAI Rollback Runbook

## Overview
This runbook provides procedures for rolling back AstrovoxAI deployments when issues are detected.

## When to Rollback
Rollback should be initiated when:
- Error rate exceeds 5% baseline
- Latency p99 increases by > 2x baseline
- Health checks fail consistently
- Database connection failures
- Critical security vulnerability discovered in deployed version
- Data corruption or loss detected

## Rollback Decision Tree
```
Issue Detected
    │
    ├─► Is it a known issue with a fix available?
    │   ├─► YES → Deploy fix (fast-forward)
    │   └─► NO → Continue
    │
    ├─► Is error rate < 5%?
    │   ├─► YES → Monitor, investigate root cause
    │   └─► NO → Rollback immediately
    │
    └─► Is health check failing?
        ├─► YES → Rollback immediately
        └─► NO → Monitor, apply mitigations
```

## Quick Rollback (GitHub Actions)

### Automatic Rollback
The CI/CD pipeline includes automatic rollback triggers:

```yaml
# Triggered when:
# - Health check fails for 3 consecutive attempts
# - Error rate exceeds 5% for 2 minutes
# - Deployment times out after 30 minutes
```

### Manual Rollback
```bash
# List available versions
git tag --sort=-version:refname | head -10

# Trigger rollback workflow
gh workflow run rollback.yml \
  --field environment=production \
  --field target_version=v1.2.3 \
  --field reason="Production error rate exceeded threshold"

# Monitor rollback progress
gh run watch $(gh run list --workflow=rollback.yml --limit=1 --json databaseId --jq '.[0].databaseId')
```

## Rollback Methods

### Method 1: GitHub Actions Rollback (Recommended)
```bash
# Full rollback with validation
gh workflow run rollback.yml \
  -f environment=production \
  -f target_version=<VERSION> \
  -f reason="<REASON>"

# Monitor the workflow
gh run list --workflow=rollback.yml --limit=5
gh run view <run-id>
```

### Method 2: ECS Rollback (AWS)
```bash
# Get previous task definition
aws ecs list-task-definitions \
  --family-prefix astrovox-backend \
  --sort DESC \
  --max-items 5

# Update service with previous task definition
aws ecs update-service \
  --cluster astrovox-production \
  --service astrovox-backend \
  --task-definition astrovox-backend:<previous-version>

# Wait for stability
aws ecs wait services-stable \
  --cluster astrovox-production \
  --services astrovox-backend
```

### Method 3: Kubernetes Rollback
```bash
# Rollback to previous revision
kubectl rollout undo deployment/astrovox-backend -n production
kubectl rollout undo deployment/astrovox-frontend -n production

# Check rollback status
kubectl rollout status deployment/astrovox-backend -n production --timeout=600s
kubectl rollout status deployment/astrovox-frontend -n production --timeout=600s

# Verify rollback
kubectl get pods -n production
kubectl describe deployment astrovox-backend -n production
```

### Method 4: Helm Rollback
```bash
# List release history
helm history astrovox -n production

# Rollback to previous release
helm rollback astrovox <revision> -n production

# Verify rollback
helm status astrovox -n production
kubectl rollout status deployment/astrovox-backend -n production
```

## Rollback Validation

After rollback, verify:
```bash
# 1. Health checks pass
curl -f https://api.astrovox.ai/health/live || exit 1
curl -f https://api.astrovox.ai/health/ready || exit 1

# 2. No errors in logs
kubectl logs -l app=astrovox-backend -n production --since=5m | grep -i error || echo "No errors"

# 3. Error rate back to baseline
curl -s https://api.astrovox.ai/metrics | grep http_requests_total

# 4. Database connectivity
kubectl exec -it deployment/astrovox-backend -n production -- \
  python -c "from app.db import engine; print('DB OK')"

# 5. Redis connectivity
kubectl exec -it deployment/astrovox-backend -n production -- \
  python -c "from app.redis import redis_client; redis_client.ping(); print('Redis OK')"
```

## Post-Rollback Actions

### 1. Create Incident Issue
```bash
gh issue create \
  --title "[INCIDENT] Production rollback to <version>" \
  --body "## Rollback Details
- **Environment**: production
- **Target Version**: <version>
- **Previous Version**: <previous-version>
- **Reason**: <reason>
- **Triggered by**: @<user>
- **Time**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Impact
- [ ] Users affected: <number>
- [ ] Duration: <time>
- [ ] Data loss: yes/no

## Root Cause
[To be filled after investigation]

## Fix
[To be filled after investigation]" \
  --label incident,blocked,needs-investigation
```

### 2. Notify Team
```bash
# Slack notification
curl -X POST "${{ secrets.SLACK_WEBHOOK }}" \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🚨 Production rollback initiated",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*🚨 Production Rollback*\n• Target: <version>\n• Reason: <reason>\n• Action: Investigating root cause"
        }
      }
    ]
  }'
```

### 3. Investigate Root Cause
```bash
# Collect logs
kubectl logs -l app=astrovox-backend -n production --since=1h > rollback-logs.txt
kubectl logs -l app=astrovox-frontend -n production --since=1h > rollback-frontend-logs.txt

# Check metrics
curl -s https://api.astrovox.ai/metrics > rollback-metrics.txt

# Download artifacts from failed deployment
gh run download <failed-run-id> -n production

# Check database state
kubectl exec -it deployment/astrovox-backend -n production -- \
  python -c "from app.db import session; print(session.execute('SELECT COUNT(*) FROM users').scalar())"
```

### 4. Fix and Redeploy
```bash
# Create fix branch
git checkout -b fix/incident-<issue-number>

# Apply fix
# ... make changes ...

# Commit and push
git add .
git commit -m "fix: resolve incident <issue-number> - <description>"
git push origin fix/incident-<issue-number>

# Create PR
gh pr create \
  --title "fix: resolve incident <issue-number>" \
  --body "Fixes the issue that caused the production rollback." \
  --label incident,needs-review

# After PR merge, monitor deployment
gh run watch $(gh run list --workflow=ci.yml --limit=1 --json databaseId --jq '.[0].databaseId')
```

## Rollback Metrics to Track
- Time to detect issue (target: < 5 minutes)
- Time to decide to rollback (target: < 2 minutes)
- Time to execute rollback (target: < 5 minutes)
- Total incident duration (target: < 15 minutes)
- User impact (target: 0 data loss)

## Emergency Contacts
- **On-Call Engineer**: Check PagerDuty/OpsGenie
- **DevOps Team**: #astrovox-devops Slack channel
- **Platform Team**: #astrovox-platform Slack channel
