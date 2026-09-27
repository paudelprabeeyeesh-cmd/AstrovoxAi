# Production Platform

Deployments, canary releases, model serving, and production operations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRODUCTION PLATFORM                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   CI/CD      │    │   Deployment │    │   Canary             │  │
│  │   Pipeline   │───►│   Engine     │───►│   Release            │  │
│  └──────────────┘    └──────────────┘    └──────────┬───────────┘  │
│                                                     │               │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────▼───────────┐  │
│  │   Model      │    │   Inference  │    │   Observability     │  │
│  │   Registry   │    │   Server     │    │   & Alerting        │  │
│  └──────┬───────┘    └──────────────┘    └──────────────────────┘  │
│         │                                                            │
│  ┌──────▼────────────────────────────────────────────────────────┐  │
│  │                    Rollback & Recovery                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │  │
│  │  │  Automated   │  │  Health      │  │  Incident            │  │  │
│  │  │  Rollback    │  │  Checks      │  │  Response            │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Deployment Engine

### Overview

The deployment engine manages zero-downtime deployments across environments.

```python
from astrovox_ai.backend.app.production.deployment import (
    DeploymentEngine,
    DeploymentConfig,
    Environment
)

config = DeploymentConfig(
    environment=Environment.PRODUCTION,
    strategy="rolling",  # or "blue_green", "canary"
    health_check_url="/health/ready",
    health_check_timeout=300,
    rollback_on_failure=True,
    min_ready_seconds=10
)

engine = DeploymentEngine(config)
engine.deploy(
    image_tag="v2.0.1",
    services=["backend", "frontend"]
)
```

### Deployment Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Rolling | Gradually replace pods | Standard deployments |
| Blue-Green | Switch traffic between identical environments | Zero-downtime, instant rollback |
| Canary | Gradual traffic shift with monitoring | High-risk changes |

## Canary Releases

### Configuration

```python
from astrovox_ai.backend.app.production.canary import (
    CanaryRelease,
    CanaryConfig
)

config = CanaryConfig(
    initial_traffic_percentage=5,
    increment_percentage=10,
    increment_interval_minutes=15,
    success_criteria={
        "error_rate_threshold": 0.01,
        "latency_p95_threshold_ms": 500,
        "success_rate_threshold": 0.99
    },
    auto_promote=True,
    rollback_on_failure=True
)

canary = CanaryRelease(config)
canary.deploy(
    image_tag="v2.1.0",
    services=["backend"]
)
```

### Canary Workflow

1. Deploy canary with 5% traffic
2. Monitor metrics for 15 minutes
3. If success criteria met, increase to 15%
4. Repeat until 100%
5. If failure detected, rollback automatically

## Model Serving

### Inference Server

```python
from astrovox_ai.ai_core.production.serving import (
    ModelServer,
    ServerConfig,
    ModelEndpoint
)

config = ServerConfig(
    max_batch_size=32,
    max_wait_time_ms=10,
    tensor_parallel_size=4,
    pipeline_parallel_size=1,
    enable_kv_cache=True,
    enable_prefix_caching=True
)

server = ModelServer(config)

# Register model
server.register_model(
    model_id="gpt-4-astrovox",
    model_path="/models/gpt-4-astrovox",
    endpoint=ModelEndpoint.CHAT_COMPLETIONS
)

# Start serving
server.start(port=8000)
```

### Load Balancing

| Strategy | Description |
|----------|-------------|
| Round Robin | Distribute evenly across instances |
| Least Latency | Route to fastest instance |
| Least Connections | Route to least busy instance |
| Consistent Hashing | Route by model ID for cache affinity |

### Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: astrovox-inference
spec:
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: inference_queue_depth
        target:
          type: AverageValue
          averageValue: "10"
```

## Health Checks

### Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 60
  periodSeconds: 10
  failureThreshold: 3
```

### Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 2
```

### Startup Probe

```yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 5
  failureThreshold: 30
```

## Observability

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `inference_requests_total` | Counter | Total inference requests |
| `inference_latency_seconds` | Histogram | Request latency distribution |
| `inference_tokens_generated_total` | Counter | Total tokens generated |
| `inference_queue_depth` | Gauge | Current queue depth |
| `inference_batch_size` | Histogram | Batch size distribution |
| `model_load_time_seconds` | Gauge | Model loading time |
| `gpu_memory_usage_bytes` | Gauge | GPU memory utilization |
| `kv_cache_hit_rate` | Gauge | KV cache hit ratio |

### Dashboards

- **Inference Dashboard**: Request rate, latency, tokens/sec, queue depth
- **Model Dashboard**: Per-model metrics, error rates, fallback usage
- **Resource Dashboard**: GPU/CPU/memory utilization, pod counts
- **Cost Dashboard**: Token costs per model, per tenant, per day

## Rollback & Recovery

### Automated Rollback

```python
from astrovox_ai.backend.app.production.rollback import (
    AutoRollback,
    RollbackPolicy
)

policy = RollbackPolicy(
    error_rate_threshold=0.05,
    latency_p99_threshold_ms=2000,
    consecutive_failures=3,
    check_interval_seconds=30
)

rollback = AutoRollback(policy)
rollback.monitor_and_rollback_if_needed(
    deployment_id="deploy-123",
    previous_image_tag="v2.0.0"
)
```

### Disaster Recovery

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Single pod failure | < 1 min | 0 | Kubernetes self-healing |
| AZ failure | < 5 min | < 1 min | Cross-AZ failover |
| Region failure | < 30 min | < 5 min | Cross-region failover |
| Data corruption | < 4 hours | < 1 hour | Restore from backup |

## Configuration Management

### Environment Configuration

```python
from astrovox_ai.backend.app.production.config import (
    ProductionConfig,
    ConfigSource
)

config = ProductionConfig(
    source=ConfigSource.CONFIGMAP,
    namespace="astrovox-production",
    configmap_name="astrovox-config",
    secret_name="astrovox-secrets"
)

# Dynamic configuration reload
config.watch_for_changes()
```

### Feature Flags

```python
from astrovox_ai.backend.app.production.feature_flags import FeatureFlags

flags = FeatureFlags()

if flags.is_enabled("new_rag_pipeline", default=False):
    # Use new RAG implementation
    pass
else:
    # Use legacy implementation
    pass
```

## Scheduling

### Kubernetes Cron Jobs

```python
from astrovox_ai.backend.app.production.scheduling import (
    ScheduledJob,
    JobConfig
)

job = ScheduledJob(
    config=JobConfig(
        schedule="0 2 * * *",  # Daily at 2 AM
        command=["python", "scripts/daily_cleanup.py"],
        resources={"cpu": "500m", "memory": "1Gi"}
    )
)
job.create()
```

### Task Queues

```python
from astrovox_ai.backend.app.production.task_queue import (
    TaskQueue,
    TaskPriority
)

queue = TaskQueue("default")

# Enqueue task
queue.enqueue(
    task="generate_report",
    args={"report_type": "daily"},
    priority=TaskPriority.LOW,
    schedule="0 6 * * *"  # Daily at 6 AM
)
```
