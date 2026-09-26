# AstrovoxAI Capacity Planning Runbook

## Overview

This runbook defines the process for monitoring resource utilization and planning capacity expansions before constraints impact users.

## Key Metrics

- CPU utilization per service.
- Memory utilization per service.
- Database connection pool usage.
- Queue depth and consumer lag.
- Request rate and concurrency.

## Review Schedule

| Review Cadence | Audience | Focus |
|----------------|----------|-------|
| Weekly | Platform team | Trends and early warnings |
| Monthly | Engineering leads | Growth projections |
| Quarterly | Leadership | Budget and procurement |

## Thresholds

| Resource | Warning | Critical |
|----------|---------|----------|
| CPU | > 70% for 1 hour | > 85% for 15 minutes |
| Memory | > 75% for 1 hour | > 90% for 15 minutes |
| DB pool | > 60% | > 80% |
| Queue depth | > 500 | > 2000 |

## Analysis Steps

```bash
# Current utilization
kubectl top pods -n production
kubectl top nodes

# Database metrics
curl -s https://api.astrovox.ai/metrics | grep -E "(pool|connections|latency)"

# Request trends
curl -s https://api.astrovox.ai/metrics | grep http_requests_total
```

## Capacity Planning Worksheet

| Resource | Current | 3-Month Forecast | 6-Month Forecast | Action |
|----------|---------|------------------|------------------|--------|
| Backend CPU | | | | |
| Backend Memory | | | | |
| Database Storage | | | | |
| Redis Memory | | | | |

## Scaling Actions

- Vertical scaling: Increase instance size.
- Horizontal scaling: Add replicas.
- Database: Read replicas or sharding.
- Cache: Increase Redis memory or add cluster nodes.

## Approval

Capacity expansions require:

1. Platform team review.
2. Budget approval (if cost impact > $500/month).
3. Change management ticket.
