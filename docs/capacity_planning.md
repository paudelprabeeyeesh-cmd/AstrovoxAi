# Capacity Planning

## Current Limits

| Resource | Current | Target | Headroom |
|----------|---------|--------|----------|
| API Requests/min | 1000 | 10,000 | 10x |
| Concurrent WebSockets | 100 | 5,000 | 50x |
| Database Connections | 10 | 100 | 10x |
| Redis Memory | 512MB | 4GB | 8x |
| LLM Tokens/day | 1M | 10M | 10x |

## Scaling Triggers

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| CPU utilization | >70% | >85% | Scale up/out |
| Memory utilization | >75% | >90% | Scale up/out |
| DB connections | >50 | >80 | Increase pool |
| Queue depth | >1000 | >5000 | Add workers |
| Error rate | >1% | >5% | Investigate |

## Cost Estimates

| Tier | Users | Monthly Cost |
|------|-------|--------------|
| Small | 1,000 | $500 |
| Medium | 10,000 | $5,000 |
| Large | 100,000 | $50,000 |
| Enterprise | 1,000,000 | $500,000 |

## Growth Projections
- Month 1-3: 1,000 users
- Month 4-6: 10,000 users
- Month 7-12: 100,000 users
