# Platform Outage Runbook

## Overview

This runbook covers platform-wide or major component outages requiring coordinated response.

## Detection

### Automated Detection

- Monitoring dashboards show service down or latency spike.
- PagerDuty alert fires for `DownOrPanicking` or `HighErrorRate`.
- Health check endpoints return non-200 status codes.
- Customer reports on support channels.

### Manual Detection

- Customer reports via support tickets
- Social media monitoring
- Internal team Slack messages
- Status page reports

## Triage

### 1. Confirm Outage Scope

```bash
# Check overall health
curl -f https://api.astrovox.ai/health/detailed || echo "Service down"

# Check specific services
curl -s https://api.astrovox.ai/health/detailed | jq '.services'

# Check pod status
kubectl get pods -n production
kubectl get pods -n production --field-selector=status.phase!=Running

# Check recent deployments
gh run list --workflow=ci.yml --limit=5
```

### 2. Determine Scope

| Scope | Indicators | Response |
|-------|-----------|----------|
| API | `/health/detailed` failing, 5xx errors | Backend team |
| Embeddings | `/embeddings/status` failing | ML platform team |
| Chat | `/chat/message` failing | Backend team |
| Infrastructure | Multiple services down | Platform team |
| Database | DB connection failures | Platform team |
| External Provider | Provider-specific errors | AI platform team |

### 3. Check Dashboards

- Prometheus: `http://prometheus.astrovox.ai`
- Grafana: `http://grafana.astrovox.ai/d/astrovox-main`
- Alertmanager: `http://alertmanager.astrovox.ai`

## Mitigation

### Option 1: Rollback Latest Deployment

```bash
# If correlated with recent deploy
gh workflow run rollback.yml \
  -f environment=production \
  -f target_version=<PREVIOUS_VERSION> \
  -f reason="Platform outage after deployment"
```

### Option 2: Scale Up Workers

```bash
# Scale up backend pods
kubectl scale deployment/astrovox-backend -n production --replicas=10

# Scale up frontend pods
kubectl scale deployment/astrovox-frontend -n production --replicas=5
```

### Option 3: Enable Circuit Breakers

```bash
# Protect downstream services
kubectl set env deployment/astrovox-backend -n production \
  OPENAI_CIRCUIT_BREAKER=true \
  OPENAI_TIMEOUT=5 \
  ANTHROPIC_CIRCUIT_BREAKER=true \
  ANTHROPIC_TIMEOUT=5
```

### Option 4: Switch to Fallback Providers

```bash
# Update provider routing
kubectl set env deployment/astrovox-backend -n production \
  DEFAULT_PROVIDER=groq \
  FALLBACK_PROVIDERS=openai,anthropic
```

## Communication

### Internal Communication

1. Post to #incidents Slack channel within 5 minutes
2. Include:
   - Service affected
   - Impact description
   - ETA (if known)
   - Incident commander
   - Current status

```bash
curl -X POST "${{ secrets.SLACK_WEBHOOK }}" \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🚨 *Platform Outage Declared*",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*🚨 Platform Outage Declared*\n• *Service*: <service>\n• *Issue*: <description>\n• *Impact*: <impact>\n• *Incident Commander*: @<user>\n• *Status*: Investigating"
        }
      }
    ]
  }'
```

### External Communication

1. Update status page within 10 minutes of confirmed outage
2. Send customer emails for outages > 30 minutes
3. Update support portal with known issues

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

## Recovery

### Gradual Traffic Restoration

1. Verify health checks pass
2. Restore traffic to 10%
3. Monitor for 5 minutes
4. Increase to 50%
5. Monitor for 5 minutes
6. Increase to 100%

### Post-Recovery Monitoring

```bash
# Monitor for 30 minutes post-recovery
watch -n 30 'curl -s https://api.astrovox.ai/metrics | grep http_requests_total'
```

## Post-Mortem

File incident report within 24 hours:

```markdown
## Incident Summary
- **Incident ID**: INC-2024-001
- **Severity**: P0
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
[Description of root cause]

## Remediation
- Rolled back to previous version
- Applied hotfix for root cause
- Added monitoring for early detection

## Action Items
- [ ] Add monitoring for [specific issue]
- [ ] Update runbooks with [specific procedure]
- [ ] Schedule blameless post-mortem
```

## Emergency Contacts

- **PagerDuty/On-Call**: Check on-call schedule
- **DevOps Lead**: @devops-lead
- **Engineering Manager**: @eng-manager
- **Security Team**: @security-team
