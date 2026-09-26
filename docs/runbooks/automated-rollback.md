# Automated Rollback Runbook

This runbook covers automated rollback procedures based on SLO violations and error budget exhaustion.

## Overview

Automated rollbacks are triggered when:
- Consecutive health check failures exceed `max_consecutive_failures`
- Error budget burn rate exceeds `fast_burn_threshold`
- Error budget is exhausted with sustained burn rate

## Configuration

Rollback policy is configured in `backend/app/reliability/automated_rollback.py`:

```python
policy = RollbackPolicy(
    error_budget_fast_burn_threshold=14.4,
    error_budget_slow_burn_threshold=3.0,
    max_consecutive_failures=3,
    cooldown_seconds=600,
)
```

## Manual Rollback

```bash
# Via CLI
astrovox rollback --version v1.2.3 --reason "SLO violation"

# Via GitHub Actions
gh workflow run rollback.yml \
  -f environment=production \
  -f target_version=v1.2.3 \
  -f reason="SLO violation"
```

## Verification

After rollback, verify recovery:

```bash
curl -f https://api.astrovox.ai/health/detailed || echo "Still down"
kubectl rollout status deployment/astrovox-backend -n production
```

## Monitoring

- Check Grafana for SLO status
- Monitor error budget recovery
- Review incident timeline in `backend/app/reliability/incident_manager.py`

## Post-Rollback

1. Mark incident as resolved
2. Update status page if needed
3. Schedule post-mortem
4. Fix root cause
5. Re-deploy with fix
