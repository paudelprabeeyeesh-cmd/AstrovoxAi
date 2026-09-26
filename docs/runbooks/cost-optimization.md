# AstrovoxAI Cost Optimization Runbook

## Overview

This runbook documents processes for monitoring and optimizing cloud and service costs.

## Cost Visibility

```python
from app.reliability.cost_optimizer import CostOptimizer

optimizer = CostOptimizer()
optimizer.register("compute_backend", daily_cost=45.0, suggestion="Resize instances to 2 vCPU / 4GiB")
optimizer.register("database_rds", daily_cost=30.0, suggestion="Enable auto-scaling for off-peak hours")
optimizer.register("storage_s3", daily_cost=12.0, suggestion="Move infrequent objects to Glacier")
optimizer.register("ai_api", daily_cost=80.0, suggestion="Implement caching for repeated prompts")

print(optimizer.report())
print(optimizer.suggestions())
```

## Optimization Actions

### Compute

- Right-size instances based on utilization.
- Use spot/preemptible instances for non-critical workloads.
- Scale to zero during off-peak hours.

### Storage

- Implement lifecycle policies for backups.
- Deduplicate repeated model weights and datasets.
- Use compressed formats.

### AI / API Costs

- Cache frequent prompts and responses.
- Batch inference requests.
- Use smaller models for simple tasks.

## Review Schedule

- Weekly: Automated cost report via dashboard.
- Monthly: Cost review with engineering leads.
- Quarterly: Vendor negotiation and commitment planning.

## Budget Alerts

| Threshold | Action |
|-----------|--------|
| 80% of monthly budget | Notify engineering lead |
| 95% of monthly budget | Notify CTO and pause non-essential spend |
| 100% of monthly budget | Emergency review and spending freeze |

## Cost Dashboard

Access the cost optimization dashboard at: `monitoring/dashboards/astrovox-cost.json`
