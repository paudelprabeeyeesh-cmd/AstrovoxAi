# Safety Incident Runbook

## Overview

This runbook guides responders through a safety incident involving harmful content, jailbreaks, PII leaks, or model misbehavior.

## Detection

### Automated Detection

- Alert fired in Prometheus (`SafetyViolationSpike`)
- Automated safety module raises `SafetyAlert` event
- Content moderation pipeline flags output
- PII detector triggers alert

### Manual Detection

- Human moderator flags content in admin console
- User reports unsafe content
- Security team identifies vulnerability
- External researcher discloses issue

## Triage

### 1. Acknowledge Alert

```bash
# Acknowledge in PagerDuty
# Notify #safety-incidents Slack channel
```

### 2. Identify Affected Components

```bash
# Check affected model
curl -s https://api.astrovox.ai/health/detailed | jq '.services'

# Check affected endpoint
grep -r "endpoint" /var/log/astrovox/safety.log | tail -20

# Check affected user/org
curl -s https://api.astrovox.ai/api/v1/safety/audit?hours=1 | jq '.incidents[] | select(.severity == "critical")'
```

### 3. Determine Severity

| Severity | Description | Examples | Response Time |
|----------|-------------|----------|---------------|
| Critical | Active data leak, ongoing exploitation, self-harm content | Active PII leak, jailbreak exploit | < 5 minutes |
| High | PII exposure, hate speech, violent content | User PII exposed, hate speech generated | < 15 minutes |
| Medium | Bias flags, excessive refusal, moderate policy violations | Bias in output, unjustified refusal | < 1 hour |
| Low | Minor policy violations, edge cases | Mild policy violation | < 4 hours |

## Response

### Immediate Actions (Critical/High)

1. Enable emergency block on affected model/endpoint
2. Quarantine offending prompt/response pair
3. Notify org admin and affected user
4. Document incident in safety incident tracker

```python
from astrovox_ai.backend.app.safety_routes import SafetyController

controller = SafetyController()

# Block affected model
controller.block_model(
    model_id="gpt-4",
    reason="Active jailbreak exploitation",
    duration_hours=24
)

# Quarantine content
controller.quarantine_content(
    content_id="msg-123",
    reason="PII exposure"
)
```

### Investigation

1. Pull logs from safety modules
2. Reproduce issue with EvaluationHarness
3. Check for prompt injection vectors
4. Analyze model behavior

```bash
# Pull safety logs
kubectl logs -l app=astrovox-backend -n production --since=1h | grep -i safety > safety-incident-logs.txt

# Reproduce issue
python -m app.safety.evaluation_harness --prompt "offending prompt here"

# Check injection vectors
python -m app.safety.injection_defense --analyze "offending prompt"
```

### Remediation

| Issue Type | Remediation |
|------------|-------------|
| Prompt injection | Update blocklists, strengthen classifiers |
| Jailbreak | Update jailbreak detectors, add new patterns |
| PII leak | Update PII detectors, tighten redaction rules |
| Harmful content | Update moderation classifiers |
| Model misbehavior | Switch to fallback model, retrain |
| System issue | Patch and deploy |

## Communication

### Internal Communication

Post status updates every 15 minutes in #safety-incidents:

```bash
curl -X POST "${{ secrets.SLACK_SAFETY_WEBHOOK }}" \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🛡️ *Safety Incident Update*",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*🛡️ Safety Incident Update*\n• *Severity*: <severity>\n• *Status*: <status>\n• *Next Update*: <time>"
        }
      }
    ]
  }'
```

### External Communication

For critical incidents:
- Email `safety@astrovox.ai` and `legal@astrovox.ai`
- Update status page if user-facing impact confirmed
- Notify affected users per GDPR requirements

## Post-Incident

### Documentation

Create safety incident report within 48 hours:

```markdown
## Safety Incident Report

- **Incident ID**: SAFETY-2024-001
- **Severity**: Critical
- **Reported**: 2024-01-15 14:30 UTC
- **Resolved**: 2024-01-15 16:00 UTC
- **Duration**: 90 minutes

## Timeline
- 14:30 - Alert triggered
- 14:32 - Acknowledged
- 14:35 - Root cause identified
- 14:45 - Remediation deployed
- 15:00 - Monitoring
- 16:00 - Resolved

## Root Cause
[Description]

## Remediation Steps
1. [Step 1]
2. [Step 2]

## Prevention
- [ ] Update classifiers
- [ ] Add detection rules
- [ ] Improve monitoring
```

### Follow-up Actions

1. Update safety classifiers and blocklists
2. Add new detection rules
3. Improve monitoring and alerting
4. Schedule review with Safety and Engineering leads
5. Update documentation and runbooks

## Emergency Contacts

- **Safety Team**: @safety-lead
- **Engineering Lead**: @eng-lead
- **Legal**: @legal-team
- **Security Team**: @security-team
- **On-Call**: Check PagerDuty schedule
