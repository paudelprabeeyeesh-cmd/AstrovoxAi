# Health Monitoring & Observability Guide

Production-ready monitoring setup for AstrovoxAI platform.

## Overview

This guide provides step-by-step setup for monitoring AstrovoxAI in production using industry-standard tools.

## Quick Monitoring Endpoints

The application exposes health check endpoints that can be monitored:

```bash
# Basic health check
curl http://localhost:8000/health
# Response: { "status": "OK" }

# Readiness probe (used by Kubernetes)
curl http://localhost:8000/health/readiness
# Response: { "status": "ready" }

# Liveness probe (used by Kubernetes)
curl http://localhost:8000/health/liveness
# Response: { "status": "alive" }

# User statistics and telemetry
curl http://localhost:8000/telemetry/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
# Response: { "total_events": 1234, "active_users": 42, ... }
```

## Option 1: Prometheus + Grafana (Recommended for Production)

### Prerequisites
- Docker and Docker Compose
- 2GB RAM minimum

### 1. Install Prometheus

Create `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'astravox-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scheme: 'http'

  - job_name: 'astravox-frontend'
    static_configs:
      - targets: ['localhost:80']
```

Run Prometheus:
```bash
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

Access at: http://localhost:9090

### 2. Install Grafana

```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  grafana/grafana
```

Access at: http://localhost:3000 (default: admin/admin)

### 3. Create Grafana Dashboard

1. Go to http://localhost:3000
2. Add Prometheus data source: http://prometheus:9090
3. Create new dashboard with these key metrics:
   - Request rate (requests/sec)
   - Response time (p50, p95, p99)
   - Error rate (errors/sec)
   - Database connection pool usage
   - Memory usage
   - CPU usage

### 4. Set Up Alerts

Example alert rules in `alerts.yml`:
```yaml
groups:
  - name: astravox
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: SlowResponses
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "Slow response times detected"

      - alert: HighMemoryUsage
        expr: memory_usage_bytes > 1e9
        for: 5m
        annotations:
          summary: "High memory usage detected"
```

## Option 2: Sentry (Error Tracking)

### Setup Sentry for Backend

1. Create account at https://sentry.io
2. Create project for Python
3. Install Sentry SDK:

```bash
cd 02-Backend
pip install sentry-sdk
```

4. Update `app/main.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn-here",
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)
```

5. Environment variable:
```bash
SENTRY_DSN=your-sentry-dsn-here
```

### Setup Sentry for Frontend

1. Install package:
```bash
npm install @sentry/react
```

2. Update `src/main.jsx`:

```javascript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  tracesSampleRate: 1.0,
});
```

3. Add to `.env`:
```bash
VITE_SENTRY_DSN=your-sentry-dsn-here
```

## Option 3: DataDog (Full-Stack Monitoring)

### Backend Instrumentation

1. Install DataDog agent:
```bash
cd 02-Backend
pip install ddtrace
```

2. Run with DataDog:
```bash
DD_TRACE_ENABLED=true \
DD_SERVICE=astravox-backend \
DD_ENV=production \
ddtrace-run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

3. Environment variables:
```bash
DD_AGENT_HOST=localhost
DD_AGENT_PORT=8126
DD_TRACE_SAMPLE_RATE=1.0
```

### Frontend Instrumentation

1. Install RUM SDK:
```bash
npm install @datadog/browser-rum @datadog/browser-logs
```

2. Initialize in `src/main.jsx`:
```javascript
import { datadogRum } from '@datadog/browser-rum';

datadogRum.init({
  applicationId: 'your-app-id',
  clientToken: 'your-client-token',
  site: 'datadoghq.com',
  service: 'astravox-frontend',
  env: 'production',
  version: '2.0.0',
  sessionSampleRate: 100,
  sessionReplaySampleRate: 20,
  trackUserInteractions: true,
  trackResources: true,
  trackLongTasks: true,
});
```

## Key Metrics to Monitor

### Backend Metrics
| Metric | Target | Tool |
|--------|--------|------|
| Request latency (p95) | <200ms | Prometheus, DataDog |
| Error rate | <0.1% | Sentry, Prometheus |
| DB connection pool usage | <80% | Prometheus |
| API rate limit violations | <10/hour | Application logs |
| Memory usage | <1GB | Prometheus |
| CPU usage | <70% | Prometheus |

### Frontend Metrics
| Metric | Target | Tool |
|--------|--------|------|
| Page load time | <2s | Sentry RUM |
| Time to Interactive (TTI) | <3s | Sentry RUM |
| Cumulative Layout Shift (CLS) | <0.1 | Sentry RUM |
| JavaScript errors | <1 per 1000 sessions | Sentry |
| API call success rate | >99% | DataDog RUM |

### Database Metrics
| Metric | Target | Tool |
|--------|--------|------|
| Query latency (p95) | <100ms | DataDog, Prometheus |
| Connection count | <30 | Prometheus |
| Cache hit rate | >80% | Application logs |
| Replication lag | <1s | PostgreSQL metrics |

## Alert Rules (Recommended)

### Critical Alerts
```
1. Error rate > 1% for 5 minutes
2. Response time p95 > 1 second for 10 minutes
3. Memory usage > 1.5GB for 5 minutes
4. Database connection pool > 80% for 5 minutes
```

### Warning Alerts
```
1. Error rate > 0.1% for 10 minutes
2. Response time p95 > 500ms for 10 minutes
3. Memory usage > 1GB for 10 minutes
4. API rate limit violations > 50 per hour
```

## Dashboards

### Essential Dashboard Panels

1. **Request Rate**
   - Queries per second over time
   - Breakdown by endpoint
   - Breakdown by status code

2. **Response Time**
   - P50, P95, P99 latencies
   - Histogram of response times
   - Slowest endpoints

3. **Error Tracking**
   - Error rate over time
   - Top errors by frequency
   - Error distribution by endpoint

4. **Database Health**
   - Connection pool usage
   - Query performance (p50, p95, p99)
   - Active queries count
   - Replication lag

5. **Infrastructure**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network I/O

6. **Business Metrics**
   - Active users
   - Total conversations
   - Memory entries created
   - API quota usage

## Log Aggregation

### ELK Stack (Elasticsearch, Logstash, Kibana)

1. Start ELK:
```bash
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" \
  docker.elastic.co/elasticsearch/elasticsearch:8.0.0

docker run -d --name kibana -p 5601:5601 \
  -e "ELASTICSEARCH_HOSTS=http://elasticsearch:9200" \
  docker.elastic.co/kibana/kibana:8.0.0
```

2. Configure application logging:
```python
# In app/main.py
import logging
from pythonjsonlogger import jsonlogger

handler = logging.FileHandler('logs/app.log')
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
```

3. Access Kibana: http://localhost:5601

## Docker-Based Complete Stack

Use this `docker-compose.monitoring.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.0.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200

volumes:
  prometheus_data:
  grafana_data:
  elasticsearch_data:
```

Start all monitoring services:
```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

## Health Check Scripts

### Basic Health Check
```bash
#!/bin/bash

echo "Checking AstrovoxAI health..."

# Backend
if curl -s http://localhost:8000/health | grep -q "OK"; then
  echo "✓ Backend health: OK"
else
  echo "✗ Backend health: FAILED"
fi

# Frontend
if curl -s http://localhost | grep -q "html"; then
  echo "✓ Frontend health: OK"
else
  echo "✗ Frontend health: FAILED"
fi

# API
if curl -s http://localhost:8000/docs | grep -q "Swagger"; then
  echo "✓ API Docs: OK"
else
  echo "✗ API Docs: FAILED"
fi
```

### Comprehensive Health Check
```bash
#!/bin/bash

set -e

echo "Running comprehensive health check..."

checks_passed=0
checks_failed=0

check() {
  local name=$1
  local command=$2
  
  if eval "$command" > /dev/null 2>&1; then
    echo "✓ $name"
    ((checks_passed++))
  else
    echo "✗ $name"
    ((checks_failed++))
  fi
}

check "Backend health" "curl -s http://localhost:8000/health | grep -q OK"
check "Frontend health" "curl -s http://localhost | grep -q html"
check "Database connectivity" "curl -s http://localhost:8000/health/readiness | grep -q ready"
check "API documentation" "curl -s http://localhost:8000/docs | grep -q Swagger"
check "Telemetry stats" "curl -s http://localhost:8000/telemetry/stats | grep -q total"

echo ""
echo "Checks passed: $checks_passed"
echo "Checks failed: $checks_failed"

if [ $checks_failed -eq 0 ]; then
  echo "✓ All systems healthy"
  exit 0
else
  echo "✗ Some systems unhealthy"
  exit 1
fi
```

## Runbook: Responding to Alerts

### High Error Rate
1. Check recent deployments
2. Review error logs in Sentry/ELK
3. Check database connectivity
4. Check OpenAI API status
5. Review recent code changes
6. Rollback if necessary

### Slow Responses
1. Check database query performance
2. Check API rate limiting status
3. Check backend CPU/memory usage
4. Review slow log entries
5. Consider scaling up if load is high
6. Check external API latencies (OpenAI)

### Memory Leak
1. Review recent deployments
2. Check for open database connections
3. Review application logs for errors
4. Force garbage collection if available
5. Restart services if necessary
6. Profile application with tools like py-spy

## Recommended Third-Party Services

| Service | Purpose | Cost |
|---------|---------|------|
| [Sentry](https://sentry.io) | Error tracking | Free tier available |
| [DataDog](https://www.datadoghq.com) | Full-stack monitoring | Enterprise |
| [New Relic](https://newrelic.com) | APM and monitoring | Free tier available |
| [Vercel](https://vercel.com) | Frontend hosting + analytics | Free + Pro |
| [Render](https://render.com) | Backend hosting | Free + Paid |
| [PagerDuty](https://www.pagerduty.com) | Incident management | Free + Paid |
| [OpsGenie](https://www.atlassian.com/software/opsgenie) | Alert management | Paid |

## Best Practices

1. **Set up redundancy**: Multiple backends behind load balancer
2. **Database backups**: Daily automated backups with point-in-time recovery
3. **Monitoring uptime**: Use external monitoring for your monitoring
4. **Test alerts**: Regularly test that alerts are functioning
5. **Document runbooks**: Keep incident response procedures current
6. **Gradual rollouts**: Use canary deployments for new versions
7. **Monitor third-party APIs**: Track OpenAI, Supabase, etc. status
8. **Performance budgets**: Set thresholds and monitor compliance

## Quick Start Monitoring

To get started immediately:

```bash
# 1. Start Prometheus + Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# 2. Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)

# 3. Import Grafana dashboard
# Use dashboard ID 1860 (Node Exporter)

# 4. Set up Sentry for error tracking
# Create account and add DSN to .env
```

---

**Next Step**: Integrate monitoring into your CI/CD pipeline to automatically report metrics to your APM tool on each deployment.
