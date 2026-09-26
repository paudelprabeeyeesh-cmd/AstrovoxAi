# AstrovoxAI Production Runbook Index

## Runbooks

| Runbook | Owner | Last Updated |
|---------|-------|--------------|
| [Incident Response](incident-response.md) | Platform | 2024-09-26 |
| [Deployment](deployment.md) | DevOps | 2024-09-26 |
| [Rollback](rollback.md) | DevOps | 2024-09-26 |
| [Backup Validation](backup-validation.md) | Platform | 2024-09-26 |
| [Disaster Recovery Drill](disaster-recovery-drill.md) | Platform | 2024-09-26 |
| [Capacity Planning](capacity-planning.md) | Platform | 2024-09-26 |
| [SLO Management](slo-management.md) | Platform | 2024-09-26 |
| [Cost Optimization](cost-optimization.md) | Platform | 2024-09-26 |
| [CI/CD Troubleshooting](cicd-troubleshooting.md) | DevOps | 2024-09-26 |

## Escalation Contacts

- **On-Call**: Check PagerDuty schedule
- **Platform**: #astrovox-platform
- **Security**: @security-lead
- **DevOps**: #astrovox-devops

## Health Checks

```bash
# Backend
curl -f https://api.astrovox.ai/health/detailed

# Frontend
curl -f https://astrovox.ai/ -I

# Metrics
curl -s https://api.astrovox.ai/metrics | head
```

## Monitoring Links

- Prometheus: http://prometheus.astrovox.ai
- Grafana: http://grafana.astrovox.ai
- Alertmanager: http://alertmanager.astrovox.ai
