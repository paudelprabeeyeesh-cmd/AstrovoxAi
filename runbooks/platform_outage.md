# Platform Outage Runbook

## Overview
This runbook covers platform-wide or major component outages.

## Detection
- Monitoring dashboards show service down or latency spike.
- PagerDuty alert fires for `DownOrPanicking` or `HighErrorRate`.
- Customer reports on support channels.

## Triage
1. Confirm outage scope: API, embeddings, chat, or infrastructure-wide.
2. Check `app.health` endpoints and `app.monitoring` dashboards.
3. Review recent deployments in CI/CD and `app.deployment` tags.

## Mitigation
- Roll back latest deployment if correlated with deploy time.
- Scale up workers if resource exhaustion is the cause.
- Enable circuit breakers (`app.circuit_breaker`) to protect downstream services.
- Switch to fallback providers via `app.model_fallback_router`.

## Communication
- Update status page within 10 minutes of confirmed outage.
- Notify `#incidents` with ETA and impact summary.
- Send customer emails for outages > 30 minutes.

## Recovery
- Verify health checks pass.
- Gradually restore traffic.
- Monitor for 30 minutes post-recovery.

## Post-Mortem
- File incident report within 24 hours.
- Include timeline, blast radius, root cause, and action items.
- Update runbooks and add missing alerts if gaps are found.
