# AstrovoxAI CI/CD Troubleshooting Runbook

## Overview
This runbook helps troubleshoot common CI/CD pipeline issues in the AstrovoxAI project.

## Common Issues and Solutions

### 1. Workflow Not Triggering

**Symptoms**: Push to branch doesn't trigger GitHub Actions workflow

**Diagnosis**:
```bash
# Check workflow file syntax
gh workflow list
gh workflow view ci.yml

# Check recent workflow runs
gh run list --workflow=ci.yml --limit=10

# Check if workflow is enabled
gh workflow enable ci.yml
```

**Solutions**:
- Verify `.yml` file is in `.github/workflows/`
- Check YAML syntax (use `yamllint`)
- Ensure workflow `on:` triggers match your event
- Check repository settings → Actions → Workflow permissions

### 2. Job Failing - Dependencies

**Symptoms**: `pip install` or `npm install` fails

**Diagnosis**:
```bash
# Check cache
gh run view <run-id> --log-failed

# Common causes:
# - Lock file out of sync (package-lock.json, requirements.txt)
# - Network issues during install
# - Missing system dependencies
```

**Solutions**:
```bash
# Regenerate lock files
rm package-lock.json
npm install
git add package-lock.json
git commit -m "chore: regenerate package-lock.json"

# Clear cache and retry
gh cache delete <cache-key>

# Use dependency caching properly
# In workflow: cache: 'npm' / cache: 'pip'
```

### 3. Docker Build Failing

**Symptoms**: `docker build` fails in CI

**Diagnosis**:
```bash
# Check build logs
gh run view <run-id> --log-failed

# Common causes:
# - Base image not found
# - Build context too large
# - Missing dependencies in Dockerfile
# - Non-root user creation issues
```

**Solutions**:
```bash
# Check Dockerfile syntax
docker build -f Dockerfile.backend -t test-backend .

# Verify base image exists
docker pull python:3.12-slim-bookworm

# Check build context size
du -sh . 
docker system df

# Use buildKit for better caching
export DOCKER_BUILDKIT=1
docker build --progress=plain -f Dockerfile.backend .
```

### 4. Security Scan Failures

**Symptoms**: Trivy, Grype, or other security scanners fail

**Diagnosis**:
```bash
# Check scan reports
gh run view <run-id> --log-failed

# Common causes:
# - Critical vulnerability in dependencies
# - Secret detected in code
# - Outdated base image with known CVEs
```

**Solutions**:
```bash
# Update dependencies
npm audit fix
pip install --upgrade <package>

# Update base image
# Change FROM python:3.12-slim to python:3.12-slim-bookworm

# Fix secrets
# Remove hardcoded secrets, use environment variables

# Run scans locally
trivy image <image-name>
grype <image-name>
```

### 5. Test Failures

**Symptoms**: Unit, integration, or security tests fail

**Diagnosis**:
```bash
# Check test output
gh run view <run-id> --log-failed

# Common causes:
# - Test database not available
# - Environment variables missing
# - Test data issues
# - Flaky tests
```

**Solutions**:
```bash
# Run tests locally with same environment
export DATABASE_URL=postgresql://localhost/astrovox_test
pytest tests/ -v

# Fix flaky tests
# - Add retries: @pytest.mark.flaky(reruns=3)
# - Fix race conditions
# - Add proper cleanup

# Update test data
# Ensure test fixtures are up to date
```

### 6. Deployment Failures

**Symptoms**: Deployment to staging/production fails

**Diagnosis**:
```bash
# Check deployment logs
gh run view <run-id> --log-failed

# Common causes:
# - Insufficient permissions
# - Resource constraints
# - Health check failures
# - Environment variables missing
```

**Solutions**:
```bash
# Verify Kubernetes access
kubectl cluster-info
kubectl get nodes

# Check resource quotas
kubectl describe quota -n production

# Verify secrets exist
kubectl get secrets -n production

# Check deployment status
kubectl get deployments -n production
kubectl describe deployment astrovox-backend -n production
```

### 7. Artifact Promotion Failures

**Symptoms**: Promotion workflow fails

**Diagnosis**:
```bash
# Check promotion logs
gh run view <run-id> --log-failed

# Common causes:
# - Source environment deployment not healthy
# - Target environment unavailable
# - Image not found in registry
```

**Solutions**:
```bash
# Verify source deployment
kubectl get pods -n staging
kubectl rollout status deployment/astrovox-backend -n staging

# Verify image exists
docker manifest inspect astrovoxai/backend:<tag>

# Retry promotion
gh workflow run promote.yml \
  -f source_environment=staging \
  -f target_environment=production \
  -f image_tag=<tag>
```

### 8. Workflow Timeouts

**Symptoms**: Workflow jobs timeout

**Diagnosis**:
```bash
# Check job duration
gh run view <run-id>

# Common causes:
# - Long-running tests
# - Slow network
# - Resource constraints
```

**Solutions**:
```yaml
# In workflow file, increase timeout
jobs:
  long-running-job:
    timeout-minutes: 60  # Increase from default 360
    steps:
      # ...
```

### 9. Cache Issues

**Symptoms**: Cache miss or stale cache

**Diagnosis**:
```bash
# Check cache keys
gh cache list

# Common causes:
# - Cache key changed unexpectedly
# - Cache corrupted
# - Restore keys not matching
```

**Solutions**:
```bash
# Clear specific cache
gh cache delete <cache-key>

# Use consistent cache keys
# In workflow:
# key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
# restore-keys: |
#   ${{ runner.os }}-pip-
```

### 10. Concurrency Issues

**Symptoms**: Workflow runs cancelled unexpectedly

**Diagnosis**:
```bash
# Check concurrency settings
gh workflow view ci.yml | grep -A 5 concurrency

# Common causes:
# - Same ref pushing multiple commits
# - Multiple PRs from same branch
```

**Solutions**:
```yaml
# Adjust concurrency settings
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true  # Or false if you want to queue
```

## Debugging Commands Cheat Sheet

```bash
# List recent workflow runs
gh run list --workflow=ci.yml --limit=20

# View specific run
gh run view <run-id>
gh run view <run-id> --log-failed

# Re-run failed jobs
gh run rerun <run-id> --failed

# Cancel running workflow
gh run cancel <run-id>

# Download artifacts
gh run download <run-id>

# Check workflow file syntax
gh workflow view ci.yml

# Enable/disable workflow
gh workflow enable ci.yml
gh workflow disable ci.yml

# Check secrets (names only, not values)
gh secret list

# Check variables
gh variable list
```

## Escalation Path

1. **Level 1**: Check this runbook and try solutions
2. **Level 2**: Ask in #astrovox-devops Slack channel
3. **Level 3**: Page on-call DevOps engineer
4. **Level 4**: Escalate to Engineering Manager

## Prevention

- Keep workflows simple and modular
- Use consistent caching strategies
- Pin action versions (use SHA, not `@v4`)
- Test workflow changes in a feature branch first
- Monitor workflow run times and optimize
- Set appropriate timeouts
- Use workflow_dispatch for manual interventions
