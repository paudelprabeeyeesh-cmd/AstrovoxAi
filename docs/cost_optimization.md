# AstrovoxAI Cost Optimization (FinOps)
**Version:** 1.0.0  
**Last Updated:** 2026-09-24  
**Owner:** DevOps Team  
**Review Cycle:** Monthly

---

## Table of Contents

1. [Overview](#overview)
2. [Cost Breakdown](#cost-breakdown)
3. [Optimization Strategies](#optimization-strategies)
4. [Cost Monitoring](#cost-monitoring)
5. [Budget Alerts](#budget-alerts)
6. [Action Items](#action-items)

---

## Overview

This document defines cost optimization policies for AstrovoxAI. The goal is to minimize costs while maintaining 99.9% availability and performance SLAs.

### FinOps Principles

1. **Visibility:** Track costs at the service and team level
2. **Optimization:** Right-size resources, use discounts, eliminate waste
3. **Governance:** Set budgets, alerts, and approval workflows
4. **Accountability:** Allocate costs to responsible teams

---

## Cost Breakdown

### Current Monthly Spend (Estimated)

| Service | Monthly | Yearly | Notes |
|---------|---------|--------|-------|
| **Compute** | | | |
| EKS Control Plane | $73 | $876 | Fixed |
| EC2 Worker Nodes | $300 | $3,600 | 3x t3.large |
| **Storage** | | | |
| EBS Volumes | $30 | $360 | 3x 100GB gp3 |
| S3 Storage | $20 | $240 | Backups, assets |
| **Database** | | | |
| RDS PostgreSQL | $250 | $3,000 | db.r6g.large Multi-AZ |
| ElastiCache Redis | $150 | $1,800 | cache.r6g.large x2 |
| **Networking** | | | |
| Application Load Balancer | $25 | $300 | 1 ALB |
| NAT Gateway | $65 | $780 | 3 NAT gateways |
| CloudFront | $30 | $360 | CDN |
| Data Transfer | $40 | $480 | Cross-AZ, internet |
| **Monitoring** | | | |
| CloudWatch | $15 | $180 | Logs, metrics |
| **Security** | | | |
| AWS Shield | $0 | $0 | Standard (free) |
| WAF | $10 | $120 | Web ACL |
| **Total** | **$1,008** | **$12,096** | |

### Cost by Environment

| Environment | Monthly | % of Total |
|-------------|---------|------------|
| Production | $850 | 84% |
| Staging | $120 | 12% |
| Development | $38 | 4% |

---

## Optimization Strategies

### 1. Compute Optimization

#### Reserved Instances (RI)
- **Savings:** 30-40% vs On-Demand
- **Recommendation:** 1-year Standard RI for steady-state workloads
- **Potential Savings:** $1,200/year

#### Savings Plans
- **Savings:** 30-50% vs On-Demand
- **Recommendation:** Compute Savings Plan for EKS nodes
- **Potential Savings:** $1,500/year

#### Spot Instances
- **Savings:** 60-90% vs On-Demand
- **Recommendation:** Use Spot for stateless batch jobs, CI/CD runners
- **Potential Savings:** $500/year

### 2. Storage Optimization

#### S3 Intelligent-Tiering
- **Savings:** 20-40% for infrequently accessed data
- **Recommendation:** Enable for backups older than 30 days
- **Potential Savings:** $100/year

#### EBS gp3 vs gp2
- **Savings:** 20% + independent IOPS/throughput
- **Recommendation:** Migrate to gp3
- **Potential Savings:** $200/year

### 3. Database Optimization

#### RDS Right-sizing
- **Current:** db.r6g.large (2 vCPU, 16GB)
- **Recommendation:** Monitor utilization; downsize if <50% CPU
- **Potential Savings:** $100/month

#### ElastiCache Right-sizing
- **Current:** cache.r6g.large x2
- **Recommendation:** Use cluster mode for better scaling
- **Potential Savings:** $50/month

#### Reserved DB Instances
- **Savings:** 30-45% vs On-Demand
- **Recommendation:** 1-year Reserved for RDS and ElastiCache
- **Potential Savings:** $1,000/year

### 4. Networking Optimization

#### NAT Gateway Optimization
- **Current:** 3 NAT gateways (one per AZ)
- **Recommendation:** Use single NAT gateway for non-prod; reduce data transfer
- **Potential Savings:** $400/year

#### CloudFront Optimization
- **Enable:** Compression, brotli, edge caching
- **Potential Savings:** $100/year

### 5. Scheduling

#### Non-Prod Scaling
- **Strategy:** Scale down staging/dev to 0 outside business hours
- **Savings:** 50-70% on non-prod compute
- **Potential Savings:** $500/year

#### Weekend Scaling
- **Strategy:** Reduce production replicas by 30% on weekends
- **Savings:** 15% on weekend compute
- **Potential Savings:** $200/year

---

## Cost Monitoring

### AWS Cost Explorer Queries

```bash
# Daily cost by service
aws ce get-cost-and-usage \
  --time-period Start=2026-09-01,End=2026-09-30 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE,Key=SERVICE

# Monthly cost by tag
aws ce get-cost-and-usage \
  --time-period Start=2026-09-01,End=2026-09-30 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=Environment
```

### Cost Dashboard (Grafana)

Create dashboards for:
- Daily/weekly/monthly spend
- Cost by service
- Cost by environment
- Cost per request
- Forecasted spend

### Cost Anomaly Detection

AWS Cost Anomaly Detection monitors for unusual spending patterns. Configure:
- Alert threshold: 20% above baseline
- Alert recipients: devops@astrovox.ai
- Monitor frequency: Daily

---

## Budget Alerts

### AWS Budgets Configuration

```yaml
# Monthly budget: $1,200
Budget:
  Name: astrovox-monthly-budget
  Amount: 1200
  Currency: USD
  TimeUnit: MONTHLY

Alerts:
  - Threshold: 80% ($960)
    Notification: Email + Slack
  - Threshold: 100% ($1,200)
    Notification: Email + Slack + PagerDuty
  - Threshold: 120% ($1,440)
    Notification: Email + Slack + PagerDuty (SEV2)
```

### Cost Alert Rules

| Budget | Current | 80% Alert | 100% Alert | 120% Alert |
|--------|---------|-----------|------------|------------|
| Monthly | $1,008 | $960 | $1,200 | $1,440 |
| Daily | $40 | $32 | $40 | $48 |

---

## Action Items

### Immediate (Q4 2026)

- [ ] Enable Cost Explorer and Cost Anomaly Detection
- [ ] Purchase 1-year Reserved Instances for RDS and ElastiCache
- [ ] Implement Compute Savings Plan
- [ ] Enable S3 Intelligent-Tiering for backups
- [ ] Migrate EBS volumes from gp2 to gp3
- [ ] Set up AWS Budgets with alerts

### Short-term (Q1 2027)

- [ ] Implement non-prod scheduling (scale down nights/weekends)
- [ ] Migrate CI/CD runners to Spot instances
- [ ] Right-size EKS nodes based on VPA recommendations
- [ ] Evaluate Graviton2 instances for cost savings

### Long-term (Q2 2027)

- [ ] Evaluate multi-cloud for cost arbitrage
- [ ] Implement FinOps dashboard with real-time cost tracking
- [ ] Establish chargeback/showback model for teams
- [ ] Set up automated cost optimization (e.g., terminate unused resources)

---

## Appendix

### Useful AWS CLI Commands

```bash
# List all EC2 instances with costs
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,State.Name,LaunchTime]' --output table

# List unattached EBS volumes
aws ec2 describe-volumes --filters Name=status,Values=available --query 'Volumes[*].[VolumeId,Size,State]' --output table

# List idle load balancers
aws elbv2 describe-load-balancers --query 'LoadBalancers[?State.Code==`active`].[LoadBalancerArn,CreatedTime]' --output table

# Cost forecast
aws ce get-cost-forecast \
  --time-period Start=2026-10-01,End=2026-10-31 \
  --granularity MONTHLY \
  --metric BLENDED_COST \
  --prediction-interval-level 80
```

### Cost Tracking Tags

All resources must be tagged with:
- `Project: astrovox`
- `Environment: production|staging|development`
- `Team: engineering|devops|data`
- `CostCenter: engineering`
