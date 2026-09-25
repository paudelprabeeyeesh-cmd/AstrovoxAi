# AstrovoxAI Deployment Runbook

## Overview
This runbook provides step-by-step instructions for deploying AstrovoxAI to staging and production environments.

## Prerequisites
- [ ] AWS CLI configured with appropriate credentials
- [ ] kubectl configured for target cluster
- [ ] Docker Hub or GitHub Packages credentials configured
- [ ] Helm 3.x installed
- [ ] Terraform 1.5+ installed (for infrastructure changes)
- [ ] GitHub CLI (`gh`) installed and authenticated
- [ ] Access to deployment secrets in GitHub repository secrets

## Pre-Deployment Checklist

### 1. Verify Branch and Commit
```bash
# Ensure you're on the correct branch
git checkout main  # or develop for staging
git pull origin main

# Verify the commit
git log -1 --oneline
git show --stat HEAD
```

### 2. Run CI Checks Locally (Optional)
```bash
# Backend tests
cd 02-Backend
pytest tests/ -v --tb=short

# Frontend tests
cd ..
npm run test -- --ci

# Lint checks
npm run lint
npm run typecheck
```

### 3. Verify Security Scans
```bash
# Check that security scans pass in GitHub Actions
gh run list --workflow=ci.yml --limit=5

# Review security scan results
gh run view <run-id> --log-failed
```

## Staging Deployment

### Automatic Deployment (GitHub Actions)
Staging deployments are automatically triggered on pushes to the `develop` branch.

**Workflow**: `.github/workflows/ci.yml` → `deploy-staging` job

**Environment**: `staging`
**Protection Rules**: None (auto-merge after CI passes)

### Manual Deployment
If automatic deployment fails, trigger manually:

```bash
# Using GitHub CLI
gh workflow run ci.yml -f environment=staging

# Or via GitHub UI: Actions → CI/CD Pipeline → Run workflow
```

### Post-Deployment Verification
```bash
# Check deployment status
kubectl rollout status deployment/astrovox-backend -n staging --timeout=600s
kubectl rollout status deployment/astrovox-frontend -n staging --timeout=600s

# Run smoke tests
curl -f https://staging.api.astrovox.ai/health || exit 1
curl -f https://staging.api.astrovox.ai/health/detailed || exit 1

# Check pod status
kubectl get pods -n staging
kubectl describe pods -l app=astrovox-backend -n staging

# Check logs for errors
kubectl logs -l app=astrovox-backend -n staging --tail=100 | grep -i error
```

## Production Deployment

### Automatic Deployment (GitHub Actions)
Production deployments are automatically triggered on pushes to the `main` branch.

**Workflow**: `.github/workflows/ci.yml` → `deploy-production` job
**Environment**: `production`
**Protection Rules**: Required reviewers, wait timer (optional)

### Blue-Green Deployment Strategy

1. **Build and Push Images**
   - CI builds Docker images for backend and frontend
   - Images are tagged with commit SHA and `latest`
   - Pushed to ECR (Elastic Container Registry)

2. **Deploy to ECS**
   ```bash
   # Force new deployment
   aws ecs update-service \
     --cluster astrovox-production \
     --service astrovox-backend \
     --force-new-deployment

   # Wait for stability
   aws ecs wait services-stable \
     --cluster astrovox-production \
     --services astrovox-backend
   ```

3. **Run Smoke Tests**
   ```bash
   # Health checks
   curl -f https://api.astrovox.ai/health || exit 1
   curl -f https://api.astrovox.ai/health/detailed || exit 1

   # API smoke test
   curl -f https://api.astrovox.ai/api/v1/health || exit 1
   ```

4. **Monitor Metrics**
   ```bash
   # Check error rate
   curl -s https://api.astrovox.ai/metrics | grep http_requests_total

   # Check Prometheus
   open https://prometheus.astrovox.ai/graph?g0.expr=rate(http_requests_total%5B5m%5D)
   ```

### Canary Deployment (Optional)
For high-risk changes, use canary deployment:

```bash
# Deploy canary with 10% traffic
kubectl apply -f infrastructure/progressive-delivery/canary-deployment.yaml

# Monitor canary metrics for 15 minutes
# If error rate < baseline, promote to 100%
# If error rate > baseline, rollback immediately
```

## Post-Deployment Verification

### Health Checks
```bash
# Backend health
curl -f https://api.astrovox.ai/health/live
curl -f https://api.astrovox.ai/health/ready
curl -f https://api.astrovox.ai/health/detailed

# Frontend health
curl -f https://astrovox.ai/ -I

# Database connectivity
kubectl exec -it deployment/astrovox-backend -n production -- \
  python -c "from app.db import engine; engine.connect()"

# Redis connectivity
kubectl exec -it deployment/astrovox-backend -n production -- \
  python -c "from app.redis import redis_client; redis_client.ping()"
```

### Metrics Verification
```bash
# Check Prometheus metrics
curl -s https://api.astrovox.ai/metrics | grep -E "(http_requests|errors|latency)"

# Check Grafana dashboard
open https://grafana.astrovox.ai/d/astrovox-main
```

### Log Verification
```bash
# Check for errors in last 5 minutes
kubectl logs -l app=astrovox-backend -n production --since=5m | grep -i error

# Check for specific error patterns
kubectl logs -l app=astrovox-backend -n production --since=5m | grep -E "(500|502|503|504)"
```

## Rollback Procedure

If deployment fails or issues are detected:

1. **Immediate Rollback** (within 5 minutes)
   ```bash
   # Use GitHub Actions rollback workflow
   gh workflow run rollback.yml \
     -f environment=production \
     -f target_version=<previous-tag> \
     -f reason="Deployment failed - immediate rollback"

   # Or manual ECS rollback
   aws ecs update-service \
     --cluster astrovox-production \
     --service astrovox-backend \
     --force-new-deployment \
     --task-definition astrovox-backend:<previous-task-definition>
   ```

2. **Verify Rollback**
   ```bash
   kubectl rollout status deployment/astrovox-backend -n production --timeout=600s
   curl -f https://api.astrovox.ai/health || exit 1
   ```

3. **Create Incident Issue**
   ```bash
   # Automatically created by rollback workflow, or manually:
   gh issue create \
     --title "[INCIDENT] Production rollback to <version>" \
     --body "Production was rolled back due to deployment issues." \
     --label incident,blocked
   ```

## Troubleshooting

### Pods Not Starting
```bash
# Check pod events
kubectl describe pod <pod-name> -n production

# Check image pull errors
kubectl get events -n production --field-selector reason=FailedPullImage

# Check resource constraints
kubectl top pods -n production
```

### Database Connection Issues
```bash
# Check RDS status
aws rds describe-db-instances --db-instance-identifier astrovox-ai-db

# Check security groups
aws ec2 describe-security-groups --group-ids <sg-id>

# Test connection from pod
kubectl exec -it deployment/astrovox-backend -n production -- \
  nc -zv astrovox-ai-db.xxxxxx.us-east-1.rds.amazonaws.com 5432
```

### High Error Rate
```bash
# Check application logs
kubectl logs -l app=astrovox-backend -n production --tail=500

# Check metrics
curl -s https://api.astrovox.ai/metrics | grep http_requests_total

# Rollback if error rate > 5%
```

## Emergency Contacts
- **On-Call Engineer**: Check PagerDuty/OpsGenie
- **DevOps Team**: #astrovox-devops Slack channel
- **Platform Team**: #astrovox-platform Slack channel
