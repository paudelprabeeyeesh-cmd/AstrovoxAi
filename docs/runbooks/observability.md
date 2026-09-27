# Observability Runbook

## Overview

This runbook covers observability tooling, dashboards, alerts, and troubleshooting for the AstrovoxAI platform.

## Tracing

### OpenTelemetry Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

exporters:
  jaeger:
    endpoint: jaeger:14250
  prometheus:
    endpoint: "0.0.0.0:8889"

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      exporters: [prometheus]
```

### Trace Sampling

| Environment | Sampling Rate | Description |
|-------------|---------------|-------------|
| Production | 1% | Sample 1% of traces |
| Staging | 100% | Sample all traces |
| Development | 100% | Sample all traces |

### Verify Tracing

```bash
# Check collector health
curl -f http://otel-collector:13133/health

# Check Jaeger UI
open http://jaeger.astrovox.ai

# Verify trace export
curl -s http://otel-collector:8889/metrics | grep otel
```

## Metrics

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'astrovox-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'astrovox-frontend'
    static_configs:
      - targets: ['frontend:80']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 15s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 15s
```

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | Request latency |
| `http_requests_failed_total` | Counter | Failed requests |
| `ai_requests_total` | Counter | AI API requests |
| `ai_tokens_generated_total` | Counter | Total tokens generated |
| `ai_latency_seconds` | Histogram | AI provider latency |
| `redis_connected_clients` | Gauge | Redis client count |
| `postgres_connections_active` | Gauge | Active DB connections |
| `process_cpu_seconds_total` | Counter | Process CPU usage |
| `process_resident_memory_bytes` | Gauge | Process memory usage |

### Verify Metrics

```bash
# Check Prometheus targets
curl -s http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .job, state: .health}'

# Query a metric
curl -s 'http://prometheus:9090/api/v1/query?query=http_requests_total' | jq '.data.result'

# Check metric cardinality
curl -s 'http://prometheus:9090/api/v1/query?query=count(metrics_by_label)' | jq
```

## Dashboards

### Grafana Dashboards

| Dashboard | URL | Description |
|-----------|-----|-------------|
| Backend Metrics | `/d/backend-metrics` | Request rate, latency, errors |
| AI Usage | `/d/ai-usage` | Model usage, tokens, costs |
| Database | `/d/database` | Connections, query time, replication |
| Redis | `/d/redis` | Hit rate, memory, clients |
| Infrastructure | `/d/infrastructure` | CPU, memory, network |
| SLO Tracker | `/d/slo-tracker` | Error budget, burn rate |

### Import Dashboards

```bash
# Import via Grafana API
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/dashboards/backend-metrics.json
```

## Logging

### Structured Logging

All logs use JSON structured format:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "app.chat",
  "message": "Message sent",
  "trace_id": "abc123",
  "user_id": "uuid",
  "conversation_id": 1,
  "model": "gpt-4",
  "tokens_used": 150,
  "duration_ms": 250
}
```

### Log Levels

| Level | Description | Usage |
|-------|-------------|-------|
| DEBUG | Detailed diagnostic info | Development only |
| INFO | General informational messages | Normal operations |
| WARNING | Warning messages | Recoverable issues |
| ERROR | Error messages | Failures that need attention |
| CRITICAL | Critical failures | Immediate action required |

### Log Shipping

```yaml
# fluent-bit configuration
[INPUT]
    Name              forward
    Listen            0.0.0.0
    Port              24224

[OUTPUT]
    Name            loki
    Match           *
    Host            loki
    Port            3100
```

### Verify Logging

```bash
# Check Loki for logs
curl -s "http://loki:3100/loki/api/v1/query_range?query={app=\"astrovox-backend\"}&limit=10" | jq

# Check for errors in last 5 minutes
curl -s "http://loki:3100/loki/api/v1/query?query={app=\"astrovox-backend\"} |= \"ERROR\" &limit=50" | jq
```

## Alerting

### Alertmanager Configuration

```yaml
# alertmanager.yml
route:
  receiver: 'default'
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'default'
    slack_channel:
      channel: '#alerts'
    email:
      to: ['oncall@astrovox.ai']
    pagerduty:
      service_key: '<key>'
```

### Alert Rules

| Alert | Condition | Severity | Runbook |
|-------|-----------|----------|---------|
| HighErrorRate | error_rate > 5% for 2m | P1 | [incident-response.md](incident-response.md) |
| HighLatency | p99_latency > 2s for 5m | P2 | [troubleshooting.md](troubleshooting.md) |
| DownService | health check failing | P0 | [platform_outage.md](platform_outage.md) |
| LowDiskSpace | disk_usage > 85% | P2 | [incident-response.md](incident-response.md) |
| DatabaseDown | postgres connections = 0 | P0 | [incident-response.md](incident-response.md) |
| RedisDown | redis ping failing | P1 | [incident-response.md](incident-response.md) |
| RateLimitSpike | rate_limit_429 > 100/min | P3 | [troubleshooting.md](troubleshooting.md) |

### Verify Alerts

```bash
# Check Alertmanager
curl -s http://alertmanager:9093/api/v1/alerts | jq '.data[] | {alert: .labels.alertname, state: .status.state}'

# Check firing alerts
curl -s http://alertmanager:9093/api/v1/alerts?silenced=false&inhibited=false&active=true | jq '.data[] | {alert: .labels.alertname, severity: .labels.severity}'
```

## Health Checks

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /healthz` | Basic health check |
| `GET /health/live` | Liveness probe |
| `GET /health/ready` | Readiness probe (checks dependencies) |
| `GET /health/detailed` | Detailed health with service statuses |
| `GET /metrics` | Prometheus metrics |

### Verify Health

```bash
# Basic health
curl -f https://api.astrovox.ai/healthz

# Detailed health
curl -s https://api.astrovox.ai/health/detailed | jq

# Check specific service
curl -s https://api.astrovox.ai/health/detailed | jq '.services.postgres'
```

## Troubleshooting

### Missing Metrics

```bash
# Check Prometheus targets
curl -s http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'

# Check application metrics endpoint
curl -s http://backend:8000/metrics | head -20
```

### Missing Logs

```bash
# Check fluent-bit status
curl -s http://fluent-bit:2020/api/v1/metrics | jq

# Check Loki status
curl -s http://loki:3100/ready

# Verify log format
kubectl logs -l app=astrovox-backend -n production --tail=1 | jq .
```

### Alert Storms

```bash
# Check firing alerts count
curl -s http://alertmanager:9093/api/v1/alerts?active=true | jq '.data | length'

# Silence noisy alert
curl -X POST http://alertmanager:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{"matchers": [{"name": "alertname", "value": "HighLatency", "isRegex": false}], "duration": "1h"}'
```

## Escalation

1. Check this runbook and relevant linked runbooks
2. Ask in #astrovox-platform Slack channel
3. Page on-call platform engineer
4. Escalate to Engineering Manager
