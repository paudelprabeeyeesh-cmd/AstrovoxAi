# AstrovoxAI Monitoring Stack

Complete monitoring and observability stack for AstrovoxAI.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AstrovoxAI Platform                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Backend    │    │  Frontend    │    │    Redis     │     │
│  │  (FastAPI)   │    │   (React)    │    │   (Cache)    │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                   │                   │              │
│         └───────────────────┼───────────────────┘              │
│                             │                                  │
│              ┌──────────────▼──────────────┐                   │
│              │     Docker Network          │                   │
│              │    (astravox-network)       │                   │
│              └──────────────┬──────────────┘                   │
│                             │                                  │
│  ┌──────────────────────────┼──────────────────────────┐      │
│  │                          │                          │      │
│  │  ┌──────────────┐  ┌─────▼──────┐  ┌──────────────┐│      │
│  │  │ Prometheus   │  │  Grafana   │  │   Loki       ││      │
│  │  │   :9090      │  │   :3000    │  │   :3100      ││      │
│  │  └──────┬───────┘  └─────┬──────┘  └──────┬───────┘│      │
│  │         │                │                 │          │      │
│  │  ┌──────┴───────┐  ┌─────┴──────┐  ┌──────┴───────┐│      │
│  │  │ Alertmanager │  │ Promtail   │  │   Jaeger     ││      │
│  │  │   :9093      │  │   :9080    │  │   :16686     ││      │
│  │  └──────────────┘  └────────────┘  └──────────────┘│      │
│  │                                                  │      │
│  └──────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Alerting Flow:
  Prometheus → Alertmanager → PagerDuty (critical) + Slack (all)
```

## Components

### 1. Prometheus (Metrics Collection)
- **Port:** 9090
- **Retention:** 30 days
- **Scrape Interval:** 15s
- **Config:** `prometheus.yml`

### 2. Grafana (Visualization)
- **Port:** 3000
- **Default Credentials:** admin / ${GRAFANA_PASSWORD}
- **Provisioned Datasources:** Prometheus, Loki, Jaeger
- **Provisioned Dashboards:** AstrovoxAI Production Monitoring

### 3. Loki (Log Aggregation)
- **Port:** 3100
- **Retention:** 30 days (720h)
- **Config:** `monitoring/loki-config.yaml`

### 4. Promtail (Log Collection)
- **Port:** 9080
- **Config:** `monitoring/promtail-config.yml`
- **Log Sources:** Backend, Nginx, Docker containers

### 5. Jaeger (Distributed Tracing)
- **Ports:** 16686 (UI), 14268 (collector), 14250 (gRPC), 4317 (OTLP gRPC), 4318 (OTLP HTTP)
- **Config:** Environment variables in docker-compose

### 6. Alertmanager (Alert Routing)
- **Port:** 9093
- **Config:** `monitoring/alertmanager.yml`
- **Routes:**
  - Critical → PagerDuty + Slack #incidents
  - Warning → Slack #platform
  - Info → Slack #platform

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 4GB RAM minimum
- 10GB disk space

### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:
```bash
GRAFANA_PASSWORD=your-secure-grafana-password
PAGERDUTY_ROUTING_KEY=your-pagerduty-routing-key
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/XXX/XXX
```

### 2. Start Monitoring Stack

```bash
# Start application + monitoring stack
docker compose --profile monitoring up -d

# Or start only monitoring stack
docker compose -f docker-compose.monitoring.yml --profile monitoring up -d
```

### 3. Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / ${GRAFANA_PASSWORD} |
| Prometheus | http://localhost:9090 | - |
| Loki | http://localhost:3100 | - |
| Jaeger | http://localhost:16686 | - |
| Alertmanager | http://localhost:9093 | - |

### 4. Verify Installation

```bash
# Check all services are running
docker compose ps

# Test Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test Loki
curl http://localhost:3100/ready

# Test Jaeger
curl http://localhost:16686/api/services
```

## Alert Rules

### Critical Alerts
- `BackendDown` - Backend unreachable for >1m
- `FrontendDown` - Frontend unreachable for >1m
- `RedisDown` - Redis unavailable for >1m
- `DatabaseDown` - PostgreSQL unreachable for >1m
- `CriticalErrorRate` - 5xx rate >15% for 2m
- `VerySlowResponses` - P99 latency >5s for 5m
- `CriticalMemoryUsage` - RSS >1GB for 2m
- `PodCrashLooping` - Pod restarting frequently

### Warning Alerts
- `HighErrorRate` - 5xx rate >5% for 5m
- `SlowResponses` - P95 latency >2s for 10m
- `HighMemoryUsage` - RSS >500MB for 5m
- `HighCPUUsage` - CPU >80% for 5m
- `SlowDatabaseQueries` - DB P95 >1s for 5m
- `LowCacheHitRatio` - Cache hit <50% for 10m
- `PersistentVolumeUsage` - PVC >85% full

## Grafana Dashboards

### AstrovoxAI - Production Monitoring

Panels:
1. Request Rate (rps by endpoint and status)
2. Response Time (P95/P99 by endpoint)
3. Error Rate (5xx by endpoint)
4. Active Connections (Postgres, Redis, HTTP)
5. Memory Usage (Backend RSS)
6. CPU Usage (by container)
7. AI Requests by Model
8. Cache Hit Ratio
9. Database Query P95
10. AI Request P95 Latency
11. WebSocket Connections
12. Active Users
13. Auth Attempts
14. LLM Time to First Token (P95)
15. SLO Error Budget Remaining

## PagerDuty Integration

### Setup

1. Create a PagerDuty service
2. Generate an Integration Key (Events API v2)
3. Add to `.env`:
   ```bash
   PAGERDUTY_ROUTING_KEY=your-integration-key
   ```

### Alert Routing

- **Critical alerts** → PagerDuty (immediate page) + Slack #incidents
- **Warning alerts** → Slack #platform
- **Info alerts** → Slack #platform

### Escalation Policy

| Severity | Response Time | Action |
|----------|--------------|--------|
| Critical | 5 minutes | Page on-call engineer |
| Warning | 15 minutes | Slack notification |
| Info | 1 hour | Daily digest |

## Loki / Promtail

### Log Sources

| Source | Path | Labels |
|--------|------|--------|
| Backend | `/var/log/astrovox/*.log` | job=astrovox-backend, app=astrovox-backend |
| Nginx | `/var/log/nginx/*.log` | job=nginx, app=astrovox-frontend |
| Docker | `/var/lib/docker/containers/*/*log` | job=docker, app=docker |
| System | `/var/log/syslog`, `/var/log/auth.log` | job=system, app=system |

### LogQL Queries

```logql
# Recent backend errors
{job="astrovox-backend"} |= "ERROR" | json | status_code >= 500

# Request latency distribution
sum(rate({job="astrovox-backend"} |= "request_completed" [5m])) by (path)

# Authentication failures
{job="astrovox-backend"} |= "auth" |= "failed"
```

## Jaeger Tracing

### Instrumentation

The backend uses OpenTelemetry-compatible tracing. To enable:

1. Install OpenTelemetry SDK in backend:
   ```bash
   cd 02-Backend && pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
   ```

2. Configure OTLP export:
   ```python
   from opentelemetry import trace
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor

   trace.set_tracer_provider(TracerProvider())
   tracer_provider = trace.get_tracer_provider()
   tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317")))
   ```

### Key Traces

- HTTP request lifecycle
- Database query execution
- LLM API calls
- Cache operations
- Authentication flow

## Troubleshooting

### Prometheus not scraping targets

1. Check targets page: http://localhost:9090/targets
2. Verify network connectivity between Prometheus and targets
3. Check Prometheus config syntax: `promtool check config prometheus.yml`

### Grafana not showing data

1. Verify Prometheus datasource is configured: http://localhost:3000/datasources
2. Check Prometheus query works: http://localhost:9090/graph?g0.expr=up
3. Verify time range in dashboard

### Loki not ingesting logs

1. Check Promtail status: `docker compose logs promtail`
2. Verify log files exist in mounted volumes
3. Check Loki ready endpoint: http://localhost:3100/ready

### Alertmanager not sending alerts

1. Verify configuration: `amtool check-config alertmanager.yml`
2. Check PagerDuty integration key is valid
3. Verify Slack webhook URL is correct
4. Test with `amtool alert add test_alert`

## Maintenance

### Backup

```bash
# Backup Prometheus data
docker compose exec prometheus tar czf /prometheus-backup.tar.gz /prometheus

# Backup Grafana dashboards
cp -r monitoring/grafana-dashboard.json backups/

# Backup Loki data
docker compose exec loki tar czf /loki-backup.tar.gz /loki
```

### Upgrade

```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose --profile monitoring up -d
```

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [PagerDuty Integration Guide](https://support.pagerduty.com/main/docs/events-api-v2)
