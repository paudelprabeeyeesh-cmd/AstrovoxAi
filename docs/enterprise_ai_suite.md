# Enterprise AI Suite

AI gateway, private deployments, and managed model services for enterprise customers.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ENTERPRISE AI SUITE                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Private    │    │   Model      │    │   AI Gateway         │  │
│  │   Deployments│    │   Registry   │    │   (Rate Limit +      │  │
│  │   (VPC/On-  │    │   (Fine-     │    │    Routing +         │  │
│  │    Prem)     │    │    tuned)    │    │    Observability)    │  │
│  └──────┬───────┘    └──────────────┘    └──────────┬───────────┘  │
│         │                                            │               │
│  ┌──────▼────────────────────────────────────────────▼───────────┐  │
│  │                    Inference Engine                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │  │
│  │  │  Model       │  │  Request     │  │  Response            │  │  │
│  │  │  Serving     │  │  Routing     │  │  Processing         │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Data       │    │   Fine-      │    │   Evaluation         │  │
│  │   Isolation  │    │   Tuning     │    │   & Validation       │  │
│  │   (Per-      │    │   Pipelines  │    │   Suite              │  │
│  │   tenant)    │    │              │    │                      │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Private Deployments

### VPC Deployment

Deploy AstrovoxAI within your virtual private cloud for maximum data isolation.

```python
from astrovox_ai.backend.app.enterprise_suite.private_deployment import (
    VPCDeployment,
    DeploymentConfig
)

config = DeploymentConfig(
    vpc_id="vpc-12345",
    subnet_ids=["subnet-1", "subnet-2"],
    security_group_ids=["sg-12345"],
    domain="ai.yourcompany.com",
    ssl_cert_arn="arn:aws:acm:...",
    private_subnets_only=True
)

deployment = VPCDeployment(config)
deployment.deploy()
```

### On-Premises Deployment

Deploy on your own infrastructure with full control.

```python
from astrovox_ai.backend.app.enterprise_suite.on_prem import (
    OnPremDeployment,
    HardwareConfig
)

hardware = HardwareConfig(
    gpu_nodes=4,
    gpus_per_node=8,
    cpu_cores=64,
    memory_gb=512,
    storage_gb=10000,
    network_gbps=100
)

deployment = OnPremDeployment(hardware)
deployment.install()
```

## AI Gateway

Centralized access point for all AI services within the enterprise.

```python
from astrovox_ai.backend.app.enterprise_suite.ai_gateway import (
    AIGateway,
    GatewayConfig,
    RateLimitPolicy
)

config = GatewayConfig(
    rate_limit_policy=RateLimitPolicy(
        requests_per_minute=1000,
        tokens_per_minute=100000,
        concurrent_requests=50
    ),
    routing_strategy="least_latency",  # or "cost_optimized", "round_robin"
    fallback_providers=["openai", "anthropic", "gemini"],
    enable_caching=True,
    cache_ttl_seconds=300
)

gateway = AIGateway(config)
response = gateway.complete(
    tenant_id="tenant-123",
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Gateway Features

| Feature | Description |
|---------|-------------|
| Request Routing | Route to optimal provider based on latency, cost, availability |
| Rate Limiting | Per-tenant rate limits with burst capacity |
| Caching | Semantic caching for repeated requests |
| Fallback | Automatic failover to backup providers |
| Observability | Request tracing, metrics, audit logging |
| Cost Tracking | Per-tenant and per-model cost attribution |

## Model Registry

Manage fine-tuned and proprietary models.

```python
from astrovox_ai.backend.app.enterprise_suite.model_registry import (
    ModelRegistry,
    ModelVersion,
    DeploymentTarget
)

registry = ModelRegistry()

# Register a fine-tuned model
model = registry.register(
    name="customer-support-gpt4",
    base_model="gpt-4",
    fine_tuning_job_id="ft-job-123",
    description="Fine-tuned for customer support",
    tags=["support", "production"]
)

# Deploy to specific target
registry.deploy(
    model_id=model.id,
    target=DeploymentTarget.GATEWAY,
    traffic_percentage=100
)

# A/B test
registry.deploy(
    model_id=model.id,
    target=DeploymentTarget.GATEWAY,
    traffic_percentage=10,
    variant_name="experiment-v1"
)
```

## Fine-Tuning Pipelines

Enterprise-grade fine-tuning with data isolation.

```python
from astrovox_ai.backend.app.enterprise_suite.fine_tuning import (
    FineTuningPipeline,
    TrainingConfig
)

config = TrainingConfig(
    base_model="llama-2-7b",
    epochs=3,
    batch_size=8,
    learning_rate=2e-4,
    lora_rank=16,
    evaluation_dataset="eval-data-v2"
)

pipeline = FineTuningPipeline(tenant_id="tenant-123")
job = pipeline.start(
    training_data="s3://tenant-data/training.jsonl",
    config=config
)

# Monitor progress
job.wait_for_completion()
job.evaluate()
job.deploy_to_gateway()
```

## Data Isolation

Each tenant's data is strictly isolated:

| Data Type | Isolation Mechanism |
|-----------|---------------------|
| Conversations | Tenant-scoped database schema |
| Fine-tuning data | Encrypted S3 prefix per tenant |
| Model checkpoints | Isolated model registry namespace |
| API keys | Tenant-scoped key store |
| Audit logs | Tenant ID in every log entry |
| Embeddings | Tenant-scoped vector namespace |

## Compliance & Governance

### Audit Logging

All AI interactions are logged for compliance:

```python
from astrovox_ai.backend.app.enterprise_suite.audit import EnterpriseAuditLogger

logger = EnterpriseAuditLogger()

logger.log_inference(
    tenant_id="tenant-123",
    user_id="user-456",
    model="gpt-4",
    prompt="...",
    response="...",
    tokens_used=150,
    latency_ms=250
)
```

### Data Residency

Configure where data is processed and stored:

```python
config.set_data_residency(
    inference_region="us-east-1",
    storage_region="us-east-1",
    backup_region="us-west-2"
)
```

### SLA Guarantees

| Tier | Uptime | Support | Latency Target |
|------|--------|---------|----------------|
| Business | 99.5% | 4 hours | p95 < 500ms |
| Enterprise | 99.9% | 1 hour | p95 < 200ms |
| Enterprise+ | 99.99% | 15 minutes | p95 < 100ms |

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/enterprise/gateway/complete` | Gateway completion |
| POST | `/api/v1/enterprise/gateway/stream` | Gateway streaming |
| GET | `/api/v1/enterprise/models` | List available models |
| POST | `/api/v1/enterprise/models/fine-tune` | Start fine-tuning |
| GET | `/api/v1/enterprise/models/{id}` | Get model details |
| POST | `/api/v1/enterprise/deployments` | Create deployment |
| GET | `/api/v1/enterprise/deployments` | List deployments |
| GET | `/api/v1/enterprise/audit/logs` | Get audit logs |
| POST | `/api/v1/enterprise/compliance/export` | Data export |
