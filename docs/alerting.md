# Alerting Configuration

## Alert Rules

### Critical Alerts
- **ServiceDown**: `/health` returns 503 for >1 minute
  - Channel: #incidents, PagerDuty
  - Severity: P1
  - Auto-remediation: restart service

- **HighErrorRate**: Error rate >5% for >5 minutes
  - Channel: #incidents, on-call
  - Severity: P1

- **DatabaseDown**: PostgreSQL unreachable
  - Channel: #incidents, DBA, on-call
  - Severity: P1

- **RedisDown**: Redis unreachable
  - Channel: #incidents, on-call
  - Severity: P2

### Warning Alerts
- **HighLatency**: p99 latency >2s for >10 minutes
  - Channel: #platform
  - Severity: P3

- **HighMemory**: Memory usage >85%
  - Channel: #platform
  - Severity: P3

- **DiskUsage**: Disk usage >80%
  - Channel: #platform
  - Severity: P3

## Notification Channels
- PagerDuty: Critical alerts
- Slack #incidents: All incidents
- Slack #platform: Warnings
- Email: Daily digest

## Silence Rules
- Planned maintenance: 1 hour before to 1 hour after
- Known issues: Until resolved

## Runbook Links
- [ServiceDown](./runbooks/service-down.md)
- [HighErrorRate](./runbooks/high-error-rate.md)
- [DatabaseDown](./runbooks/database-down.md)
