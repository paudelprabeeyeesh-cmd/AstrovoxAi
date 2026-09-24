# AstrovoxAI Capacity Planning
**Version:** 1.0.0  
**Last Updated:** 2026-09-24  
**Owner:** DevOps Team  
**Review Cycle:** Monthly

---

## Table of Contents

1. [Overview](#overview)
2. [Current Capacity](#current-capacity)
3. [Growth Projections](#growth-projections)
4. [Scaling Policies](#scaling-policies)
5. [Load Testing](#load-testing)
6. [Cost Analysis](#cost-analysis)

---

## Overview

This document defines capacity planning policies for AstrovoxAI. It includes current capacity metrics, growth projections, and scaling thresholds.

### Key Metrics

| Metric | Current | Target | Alert Threshold |
|--------|---------|--------|-----------------|
| **CPU Utilization** | 45% | <70% | >80% |
| **Memory Utilization** | 60% | <75% | >85% |
| **Request Rate** | 500 RPS | 2000 RPS | >1500 RPS |
| **P95 Latency** | 250ms | <500ms | >1000ms |
| **P99 Latency** | 800ms | <2000ms | >3000ms |
| **Error Rate** | 0.1% | <0.5% | >1% |
| **Database Connections** | 40/100 | <60% | >80% |

---

## Current Capacity

### Compute (EKS)

| Component | Current | Max | Headroom |
|-----------|---------|-----|----------|
| Backend Pods | 3 | 10 | 70% |
| Backend CPU (requests) | 600m | 3000m | 80% |
| Backend Memory (requests) | 1.5Gi | 20Gi | 92.5% |
| Frontend Pods | 2 | 10 | 80% |

### Database (RDS)

| Metric | Current | Max | Headroom |
|--------|---------|-----|----------|
| Instance Class | db.r6g.large | db.r6g.4xlarge | 75% |
| Storage | 200GB | 1000GB | 80% |
| Connections | 40/100 | 100 | 60% |
| IOPS | 3000 | 16000 | 81% |

### Cache (ElastiCache Redis)

| Metric | Current | Max | Headroom |
|--------|---------|-----|----------|
| Node Type | cache.r6g.large | cache.r6g.4xlarge | 75% |
| Memory | 6GB | 24GB | 75% |
| Connections | 200/65000 | 65000 | 99.7% |

---

## Growth Projections

### Monthly Active Users (MAU)

| Month | Projected MAU | Compute Needed | Action |
|-------|---------------|----------------|--------|
| 2026-10 | 5,000 | Current | None |
| 2026-11 | 10,000 | +50% CPU | Scale to 5 pods |
| 2026-12 | 25,000 | +100% CPU | Scale to 10 pods, upgrade DB |
| 2027-01 | 50,000 | +200% CPU | Add second EKS cluster |

### Request Volume

| Month | Requests/Day | Requests/Second | Action |
|-------|--------------|-----------------|--------|
| 2026-10 | 1M | 12 | None |
| 2026-11 | 2.5M | 29 | Scale up |
| 2026-12 | 5M | 58 | Add caching layer |
| 2027-01 | 10M | 116 | Multi-cluster |

---

## Scaling Policies

### Horizontal Pod Autoscaler (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: astrovox-backend-hpa
  namespace: astrovox
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: astrovox-backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 75
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

### Vertical Pod Autoscaler (VPA)

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: astrovox-backend-vpa
  namespace: astrovox
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: astrovox-backend
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: backend
      minAllowed:
        cpu: 100m
        memory: 256Mi
      maxAllowed:
        cpu: 2000m
        memory: 4Gi
      controlledResources: ["cpu", "memory"]
```

### Cluster Autoscaler

Configured via Terraform in `terraform/modules/eks/main.tf`:
- Scale up when pods are pending due to resource constraints
- Scale down when nodes are underutilized for 10 minutes
- Respect pod disruption budgets

---

## Load Testing

### Test Scenarios

| Scenario | Target RPS | Duration | Pass Criteria |
|----------|------------|----------|---------------|
| Baseline | 100 | 10 min | P95 <500ms, errors <0.1% |
| Expected Load | 1000 | 30 min | P95 <500ms, errors <0.5% |
| Peak Load | 2000 | 10 min | P95 <1000ms, errors <1% |
| Stress Test | 5000 | 5 min | Graceful degradation, no crashes |

### Load Testing Script

```bash
#!/bin/bash
# scripts/load-test.sh

BASE_URL="${BASE_URL:-http://localhost:8000}"
CONCURRENT_USERS="${CONCURRENT_USERS:-100}"
TEST_DURATION="${TEST_DURATION:-60s}"

echo "Running load test against ${BASE_URL}"
echo "Concurrent users: ${CONCURRENT_USERS}"
echo "Duration: ${TEST_DURATION}"

# Install k6 if not present
if ! command -v k6 &> /dev/null; then
  echo "Installing k6..."
  brew install k6  # macOS
  # Or: sudo apt-get install k6  # Ubuntu
fi

# Run test
k6 run \
  --vus ${CONCURRENT_USERS} \
  --duration ${TEST_DURATION} \
  --out influxdb=http://localhost:8086/k6 \
  tests/load-test.js

echo "Load test complete. Check Grafana dashboard for results."
```

### Load Test Script (JavaScript)

```javascript
// tests/load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const responses = http.batch([
    ['GET', 'http://localhost:8000/health'],
    ['GET', 'http://localhost:8000/api/v1/chat/conversations'],
    ['POST', 'http://localhost:8000/api/v1/chat/message', JSON.stringify({
      message: 'Hello, this is a load test',
      conversation_id: 'test-123',
    })],
  ]);

  responses.forEach((res) => {
    check(res, {
      'status is 200': (r) => r.status === 200,
      'latency < 500ms': (r) => r.timings.duration < 500,
    });
  });

  sleep(1);
}
```

---

## Cost Analysis

### Current Monthly Costs (Estimated)

| Service | Monthly Cost | % of Total |
|---------|--------------|------------|
| EKS Cluster | $150 | 15% |
| EC2 Instances | $300 | 30% |
| RDS PostgreSQL | $250 | 25% |
| ElastiCache Redis | $150 | 15% |
| Load Balancer | $50 | 5% |
| S3 Storage | $20 | 2% |
| CloudFront | $30 | 3% |
| **Total** | **$950** | **100%** |

### Cost Optimization Recommendations

1. **Reserved Instances:** Save 30-40% with 1-year reserved instances
2. **Spot Instances:** Use Spot for non-critical workloads (batch jobs)
3. **Storage Optimization:** Enable S3 Intelligent-Tiering
4. **Right-sizing:** Use VPA recommendations to right-size pods
5. **Scheduled Scaling:** Scale down non-prod environments at night
6. **CDN Optimization:** Enable compression, use edge caching

---

## Appendix

### Monitoring Dashboards

- **Capacity Dashboard:** Grafana > Dashboards > Capacity
- **Cost Dashboard:** Grafana > Dashboards > Cost (via CloudWatch)
- **Performance Dashboard:** Grafana > Dashboards > Performance

### Runbooks

- [Scale Up Runbook](docs/runbook.md#scale-up)
- [Scale Down Runbook](docs/runbook.md#scale-down)
- [Cost Alert Runbook](docs/runbook.md#cost-alerts)
