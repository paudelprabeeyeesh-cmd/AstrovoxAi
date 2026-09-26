# AstrovoxAI Disaster Recovery Drill Runbook

## Overview

This runbook defines procedures for executing disaster recovery (DR) drills to validate backup integrity, restore procedures, and team readiness.

## Objectives

- Validate backup creation and restoration within RTO/RPO targets.
- Verify team familiarity with recovery steps.
- Identify gaps in documentation or tooling.

## Drill Schedule

| Frequency | Type | Scope |
|-----------|------|-------|
| Monthly | Tabletop | Team review of procedures |
| Quarterly | Partial restore | Single service or dataset |
| Bi-annually | Full environment | Complete infrastructure failover |

## Pre-Drill Checklist

- [ ] Notify stakeholders and schedule maintenance window.
- [ ] Verify current backups exist and pass validation.
- [ ] Review `docs/runbooks/backup-validation.md`.
- [ ] Ensure monitoring alerts are paused or scoped to the drill environment.
- [ ] Assign incident commander and recorder roles.

## Drill Execution

### 1. Isolate Environment

Use a dedicated drill environment or namespace to avoid affecting production.

```bash
# Create isolated namespace
kubectl create namespace dr-drill --dry-run=client -o yaml | kubectl apply -f -
```

### 2. Restore from Backup

```bash
# Validate backup first
python -m app.reliability.backup

# Restore database backup
pg_restore -h <target-host> -U <user> -d <db> <backup_file>

# Restore object storage
aws s3 sync s3://astrovox-backups/<date>/ /tmp/dr-restore/
```

### 3. Validate Integrity

```bash
# Smoke tests
curl -f http://<dr-environment>/health/detailed

# Data consistency checks
python -m app.reliability.disaster_recovery --validate
```

### 4. Measure RTO and RPO

Record actual restore time and compare against targets.

| Metric | Target | Actual |
|--------|--------|--------|
| RTO | < 4 hours | |
| RPO | < 24 hours | |

### 5. Cleanup

```bash
# Destroy drill environment
kubectl delete namespace dr-drill --wait=true

# Restore monitoring alerts
```

## Post-Drill Review

Document results in the DR drill report:

- Drill start and end times.
- RTO/RPO achieved.
- Failures or blockers encountered.
- Action items and owners.

Create an incident ticket for any issues requiring remediation.

## Emergency Contacts

- **Incident Commander**: @on-call-lead
- **Platform Team**: #astrovox-platform
- **Security Team**: @security-lead
