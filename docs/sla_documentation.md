# SLA Documentation

## Service Level Agreement

### Service Commitment

AstrovoxAI commits to the following service levels for paid tiers:

| Metric | Target | Measurement Period |
|--------|--------|-------------------|
| Uptime | 99.9% | Monthly |
| p99 Latency | < 500ms | Monthly |
| Error Rate | < 0.1% | Monthly |
| Support Response | < 4 hours | Business days |

### Service Tiers

#### Free Tier

- No SLA guarantee
- Community support only
- Rate limited: 50 requests/day

#### Pro Tier ($49/month)

| Metric | Target |
|--------|--------|
| Uptime | 99.5% |
| p99 Latency | < 1s |
| Support Response | < 24 hours |
| Rate Limit | 10,000 requests/month |

#### Enterprise Tier (Custom)

| Metric | Target |
|--------|--------|
| Uptime | 99.9% |
| p99 Latency | < 500ms |
| Support Response | < 4 hours |
| Rate Limit | Unlimited |
| Dedicated Support | Yes |
| Custom SLA | Negotiable |

## Monitoring & Reporting

### Dashboards

- **Status Page:** https://status.astrovox.ai
- **Metrics:** https://metrics.astrovox.ai
- **Uptime:** Monitored via Pingdom / UptimeRobot

### Alerts

Customers receive alerts for:
- Service degradation
- Planned maintenance
- Security incidents

## Incident Response

### Severity Classification

| Severity | Definition | Examples | Response Time |
|----------|------------|----------|---------------|
| SEV-1 | Complete outage | API unreachable | 1 hour |
| SEV-2 | Degraded service | High latency, partial failure | 4 hours |
| SEV-3 | Minor impact | Single feature down, workaround exists | 24 hours |
| SEV-4 | Cosmetic | UI bug, documentation error | 72 hours |

### Communication

- **SEV-1:** Phone + email + status page within 15 minutes
- **SEV-2:** Email + status page within 1 hour
- **SEV-3:** Status page update within 4 hours
- **SEV-4:** Next business day

## Maintenance Windows

- **Frequency:** Weekly, Sundays 02:00-04:00 UTC
- **Notification:** 48 hours advance notice via email
- **Impact:** Brief downtime (< 5 minutes) expected

## Exclusions

SLA does not apply to:
- Scheduled maintenance
- Issues caused by customer infrastructure
- Force majeure events
- Beta/experimental features
- Third-party service outages

## Credits

### Eligibility

Customers may request service credits for SLA violations:

| Downtime | Credit |
|----------|--------|
| 99.5% - 99.9% | 10% |
| 99.0% - 99.5% | 25% |
| < 99.0% | 50% |

### Request Process

1. Contact support within 30 days of incident
2. Provide incident ID and affected timeframe
3. Credits applied to next invoice

## Data Residency

- **US:** AWS us-east-1
- **EU:** AWS eu-west-1
- **APAC:** AWS ap-southeast-1

Data residency is configurable per tenant in Enterprise tier.

## Backup & Recovery

- **RPO:** 1 hour (max data loss)
- **RTO:** 4 hours (max recovery time)
- **Backup Frequency:** Continuous (WAL archiving) + daily snapshots
- **Retention:** 30 days

## Contact

- **Support:** support@astrovox.ai
- **Emergency:** +1-555-ASTROVOX
- **Status:** https://status.astrovox.ai
