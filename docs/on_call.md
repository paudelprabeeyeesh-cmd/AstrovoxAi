# On-Call Documentation

## On-Call Rotation
- Primary on-call: See PagerDuty
- Secondary on-call: Escalation path
- Manager: Engineering lead

## Access Requirements
- Production VPN/access
- Render dashboard access
- Grafana/Prometheus access
- Jaeger tracing access
- Database read-only access
- PagerDuty mobile app

## Handoff Checklist
- [ ] Review active incidents
- [ ] Check recent deployments
- [ ] Verify monitoring dashboards
- [ ] Confirm alerting channels
- [ ] Document known issues

## Common Tasks

### Restart Service
```bash
# Render
render services restart astrovox-api

# Kubernetes
kubectl rollout restart deployment/astrovox-api -n production
```

### Database Connection Issues
```bash
# Check pool status
curl https://astrovox-api.onrender.com/health/detailed

# Restart if needed
render services restart astrovox-api
```

### Redis Issues
```bash
# Check Redis status
redis-cli ping

# Flush if needed (DANGEROUS)
redis-cli FLUSHALL
```

### Rollback Deployment
```bash
git revert HEAD
git push origin main
```

## Escalation
- If unresolved in 30 minutes: escalate to engineering lead
- If data loss suspected: escalate to CTO + security team
- If security incident: follow security incident response
