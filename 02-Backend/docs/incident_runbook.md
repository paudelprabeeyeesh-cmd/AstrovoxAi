# Incident Runbook

## Purpose
Standardize response to production incidents affecting availability, security, or data integrity.

## Severity Levels

| Level | Definition | Response Time | Examples |
|-------|------------|---------------|----------|
| SEV1 | Complete outage or data breach | 15 minutes | /health failing for all users, database unavailable |
| SEV2 | Major degradation | 30 minutes | Streaming failures, auth outages, billing errors |
| SEV3 | Minor degradation | 2 hours | Slow responses, non-critical feature failures |
| SEV4 | Cosmetic/informational | Next business day | UI bugs, documentation errors |

## Response Procedure

1. **Acknowledge**
   - Assign incident commander
   - Create incident channel
   - Update status page if customer-facing

2. **Assess**
   - Check `/health` and `/health/detailed`
   - Review Grafana dashboards
   - Check recent deployments
   - Review error rates in Prometheus

3. **Contain**
   - Rollback recent deployment if cause unknown
   - Enable maintenance mode if necessary
   - Isolate affected component

4. **Resolve**
   - Apply fix
   - Verify recovery
   - Monitor for 30 minutes

5. **Postmortem**
   - Timeline
   - Root cause
   - Impact
   - Remediation steps
   - Action items

## Common Issues

### Database Connection Exhaustion
- Symptom: `OperationalError: connection pool exhausted`
- Fix: Increase pool size in `database.py`, restart workers
- Prevention: Connection pool monitoring alerts

### Redis Outage
- Symptom: Cache misses spike, rate limiting fails
- Fix: Restart Redis, clear stale keys
- Prevention: Redis sentinel, connection pooling

### LLM Provider Outage
- Symptom: High latency, 5xx errors on `/solve`
- Fix: Switch to fallback provider in router config
- Prevention: Circuit breakers, health checks

### Memory Leak
- Symptom: OOM kills, increasing RSS
- Fix: Restart workers, identify leak with `tracemalloc`
- Prevention: Memory profiling in CI

## Escalation

- SEV1: Page on-call + notify engineering lead
- SEV2: Notify on-call + engineering lead
- SEV3: Notify engineering lead
- SEV4: Create ticket

## Contacts

- On-call: See PagerDuty rotation
- Engineering lead: See team directory
- Security: security@astrovox.ai
