# Analytics

AstrovoxAI provides built-in analytics for API usage, SDK adoption, feature engagement, and cost tracking.

## Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `api_usage` | counter | API requests by endpoint, method, status, and user tier |
| `sdk_adoption` | gauge | Active SDK users by language and version |
| `feature_usage` | counter | Feature engagement counts |
| `cost_per_request_usd` | gauge | Estimated cost per request by provider and model |

## Dashboards

Analytics dashboards are provisioned via Grafana. See `monitoring/grafana-dashboards.yml` and `monitoring/analytics.yml`.

## CLI

```bash
astrovox analytics usage --days 7
astrovox analytics latency --token <token>
astrovox analytics errors --hours 24
astrovox analytics cost --days 7
```

## Integration

Analytics events are collected by `backend/app/monitoring/analytics.py` and exported to Prometheus.
