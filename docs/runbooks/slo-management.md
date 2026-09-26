# AstrovoxAI SLO Management Runbook

## Overview

This runbook defines how to define, measure, and act on SLO compliance for AstrovoxAI services.

## SLO Definitions

| Service | SLO | Target | Window |
|---------|-----|--------|--------|
| API | Availability | 99.9% | 30 days |
| API | P95 latency < 200ms | 95% | 30 days |
| API | Error rate < 0.1% | 99.9% | 30 days |
| Training | Job success rate | 98% | 30 days |

## Measurement

```python
from app.monitoring.slo import SLOTracker

tracker = SLOTracker()
tracker.record("availability", good=True, count=1.0)
tracker.record("error_rate", good=is_success, count=1.0)

status = tracker.evaluate("availability")
```

## Error Budget Policy

| Burn Rate | Action | Owner |
|-----------|--------|-------|
| < 1.0 | No action | Platform |
| >= 1.0 and <= 3.0 | Warn and monitor | Platform |
| >= 3.0 | P2 incident and investigation | Engineering lead |
| >= 14.4 | P1 incident and freeze non-critical changes | Engineering lead |

## Review Process

- Weekly SLO review during platform standup.
- Monthly executive summary.
- Quarterly SLO target adjustment.

## Escalation

If error budget is exhausted:

1. Declare P2 incident.
2. Freeze non-critical deployments.
3. Assign incident commander.
4. Run burn rate analysis.
5. Publish postmortem within 5 business days.
