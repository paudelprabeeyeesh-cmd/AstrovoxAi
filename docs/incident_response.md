# AstrovoxAI Incident Response Playbook
**Version:** 1.0.0  
**Last Updated:** 2026-09-24  
**Owner:** DevOps Team  
**Review Cycle:** Quarterly

---

## Table of Contents

1. [Overview](#overview)
2. [Incident Severity Levels](#incident-severity-levels)
3. [Response Procedures](#response-procedures)
4. [Communication Plan](#communication-plan)
5. [Post-Incident Review](#post-incident-review)
6. [Common Incident Scenarios](#common-incident-scenarios)

---

## Overview

This playbook provides standardized procedures for responding to production incidents at AstrovoxAI. All on-call engineers must be familiar with this document.

### Incident Command System (ICS)

| Role | Responsibility |
|------|---------------|
| **Incident Commander (IC)** | Coordinates response, makes decisions, communicates status |
| **Technical Lead (TL)** | Leads technical investigation and resolution |
| **Communications Lead (CL)** | Updates stakeholders and status page |
| **Scribe** | Documents timeline and actions taken |

---

## Incident Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **SEV1** | Complete outage or data loss | 15 minutes | Site down, database lost, security breach |
| **SEV2** | Major degradation | 30 minutes | API errors >50%, latency >5s, cache down |
| **SEV3** | Minor impact, workaround exists | 2 hours | Single endpoint failing, non-critical feature |
| **SEV4** | Cosmetic or no user impact | Next business day | UI glitch, minor typo |

---

## Response Procedures

### 1. Detection & Alerting

Alerts are configured in Prometheus and routed through Alertmanager to:
- **Critical/High:** PagerDuty → Phone/SMS
- **Medium:** Slack #incidents
- **Low:** Email

### 2. Initial Response (First 5 Minutes)

```bash
# 1. Acknowledge alert in PagerDuty
# 2. Join incident bridge: https://meet.astrovox.ai/incident
# 3. Open incident channel in Slack: #incidents
# 4. Run initial diagnosis:

# Check cluster health
kubectl get nodes -o wide
kubectl get pods -n astrovox -o wide
kubectl get events -n astrovox --sort-by='.lastTimestamp' | head -20

# Check service health
curl -f https://astrovox.ai/health
curl -f https://api.astrovox.ai/health

# Check recent deployments
kubectl rollout history deployment/astrovox-backend -n astrovox
kubectl rollout history deployment/astrovox-frontend -n astrovox
```

### 3. Triage & Classification

Use the following checklist to determine severity:

- [ ] Is the entire site down? → SEV1
- [ ] Is there data loss or corruption? → SEV1
- [ ] Are critical user flows broken? → SEV2
- [ ] Is there a workaround available? → SEV3
- [ ] Is there a security vulnerability? → SEV1/SEV2

### 4. Mitigation

```bash
# Rollback recent deployment if caused by new release
kubectl rollout undo deployment/astrovox-backend -n astrovox
kubectl rollout undo deployment/astrovox-frontend -n astrovox

# Scale up if capacity issue
kubectl scale deployment/astrovox-backend -n astrovox --replicas=10

# Enable maintenance mode if needed
kubectl apply -f k8s/maintenance-mode.yaml
```

### 5. Resolution

- Document root cause
- Implement permanent fix
- Verify fix in staging before production
- Deploy fix with monitoring

### 6. Communication

| Time | Action | Audience |
|------|--------|----------|
| T+0 min | Acknowledge alert | On-call team |
| T+5 min | Initial status | Slack #incidents |
| T+15 min | Status page update | Customers |
| T+30 min | Stakeholder update | Leadership |
| T+60 min | Recovery update | Customers |
| T+End | Resolution notice | Customers |

---

## Post-Incident Review

### Timeline Documentation

Create a timeline with the following events:
- Detection time and method
- Response actions and timestamps
- Resolution time
- Customer impact duration

### Root Cause Analysis (RCA)

Use the 5 Whys technique:
1. What happened?
2. Why did it happen?
3. Why did the control fail?
4. Why was the control not effective?
5. How do we prevent recurrence?

### Action Items

| Action Item | Owner | Priority | Due Date |
|-------------|-------|----------|----------|
| [ ] Add missing alert | @devops | High | 2026-10-01 |
| [ ] Improve error handling | @backend | Medium | 2026-10-15 |
| [ ] Update runbook | @devops | Low | 2026-10-30 |

---

## Common Incident Scenarios

### Scenario 1: High Error Rate (5xx)

```bash
# 1. Identify affected services
kubectl get pods -n astrovox
kubectl logs -l app=astrovox-backend -n astrovox --tail=100

# 2. Check for recent deployments
kubectl rollout history deployment/astrovox-backend -n astrovox

# 3. Check resource constraints
kubectl top pods -n astrovox
kubectl describe hpa -n astrovox astrovox-backend-hpa

# 4. Mitigation: Rollback or scale
kubectl rollout undo deployment/astrovox-backend -n astrovox
kubectl rollout status deployment/astrovox-backend -n astrovox
```

### Scenario 2: Database Connection Issues

```bash
# 1. Check RDS status
aws rds describe-db-instances --db-instance-identifier astrovox-prod-postgres

# 2. Check connection pool
kubectl exec -it deployment/astrovox-backend -n astrovox -- \
  python -c "import psycopg2.pool; print(psycopg2.pool.ThreadedConnectionPool.__dict__)"

# 3. Check connection limits
aws rds describe-db-parameters --db-parameter-group-name astrovox-prod-db-params

# 4. Mitigation: Scale up or restart
kubectl rollout restart deployment/astrovox-backend -n astrovox
```

### Scenario 3: Redis Cache Down

```bash
# 1. Check Redis cluster status
aws elasticache describe-replication-groups \
  --replication-group-id astrovox-prod-redis

# 2. Failover if needed
aws elasticache test-failover --replication-group-id astrovox-prod-redis

# 3. Verify connectivity
redis-cli -h <redis-endpoint> ping
```

### Scenario 4: DDoS Attack

```bash
# 1. Enable AWS Shield Advanced protection
aws shield create-protection \
  --name astrovox-prod-alb \
  --resource-arn <alb-arn>

# 2. Update WAF rules
aws wafv2 update-web-acl \
  --name astrovox-waf \
  --scope CLOUDFRONT \
  --default-action Block={} \
  --rules '[...]'

# 3. Enable rate limiting
kubectl apply -f k8s/rate-limit-config.yaml
```

### Scenario 5: Data Breach / Security Incident

```bash
# 1. Isolate affected systems
kubectl cordon <compromised-node>
kubectl drain <compromised-node> --ignore-daemonsets

# 2. Rotate credentials
./scripts/rotate-secrets.sh

# 3. Review access logs
kubectl logs -l app=astrovox-backend -n astrovox | grep -i "auth"
aws cloudtrail lookup-events --lookup-attributes AttributeKey=Username,AttributeValue=<user>

# 4. Notify security team
# Send encrypted email to security@astrovox.ai
```

---

## Appendix

### Emergency Contacts

| Role | Contact |
|------|---------|
| On-call Engineer | PagerDuty |
| DevOps Lead | on-call@astrovox.ai |
| Engineering Lead | engineering@astrovox.ai |
| Security Team | security@astrovox.ai |
| AWS Support | AWS Console |

### Useful Commands

```bash
# Quick health check
kubectl get nodes && kubectl get pods -n astrovox && curl -f https://astrovox.ai/health

# Recent logs
kubectl logs -l app=astrovox-backend -n astrovox --tail=200

# Events
kubectl get events -n astrovox --sort-by='.lastTimestamp' | head -20

# Rollback
kubectl rollout undo deployment/astrovox-backend -n astrovox

# Scale
kubectl scale deployment/astrovox-backend -n astrovox --replicas=10
```
