# Observability Runbook

## Tracing
- Verify OpenTelemetry collector is healthy.
- Check trace sampling rate.

## Metrics
- Prometheus targets up at `http://localhost:9090`.
- Grafana dashboards loaded.

## Logging
- Structured JSON logs shipping to Loki.
- Alert on `level: ERROR` spikes.
