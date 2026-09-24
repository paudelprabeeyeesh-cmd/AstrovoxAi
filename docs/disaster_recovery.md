# AstrovoxAI Disaster Recovery Plan
**Version:** 1.0.0  
**Last Updated:** 2026-09-24  
**Owner:** DevOps Team  
**Review Cycle:** Quarterly

---

## Table of Contents

1. [Overview](#overview)
2. [Recovery Objectives](#recovery-objectives)
3. [Disaster Scenarios](#disaster-scenarios)
4. [Recovery Procedures](#recovery-procedures)
5. [Failover Runbook](#failover-runbook)
6. [Backup & Restore](#backup--restore)
7. [Testing & Drills](#testing--drills)
8. [Communication Plan](#communication-plan)

---

## Overview

This document defines the disaster recovery (DR) procedures for AstrovoxAI. It covers infrastructure failures, data loss, security incidents, and complete region outages.

### Architecture
- **Primary Region:** us-east-1
- **DR Region:** us-west-2
- **Database:** Amazon RDS PostgreSQL with automated backups
- **Cache:** Amazon ElastiCache Redis with Multi-AZ
- **Object Storage:** AWS S3 with cross-region replication
- **CDN:** CloudFront with origin failover

---

## Recovery Objectives

| Metric | Target | Maximum Tolerable |
|--------|--------|-------------------|
| **RPO** (Recovery Point Objective) | 15 minutes | 1 hour |
| **RTO** (Recovery Time Objective) | 1 hour | 4 hours |
| **Availability Target** | 99.9% | 99.0% |
| **Data Durability** | 99.999999999% | 99.9999999% |

---

## Disaster Scenarios

### Scenario 1: Single AZ Failure
**Probability:** Medium  
**Impact:** Low  
**Recovery:** Automated via Kubernetes pod rescheduling

### Scenario 2: EKS Cluster Failure
**Probability:** Low  
**Impact:** High  
**Recovery:** Redeploy using Terraform (1-2 hours)

### Scenario 3: RDS Primary Failure
**Probability:** Low  
**Impact:** High  
**Recovery:** Automatic failover to standby (2-5 minutes)

### Scenario 4: Complete Region Outage (us-east-1)
**Probability:** Very Low  
**Impact:** Critical  
**Recovery:** Activate DR region (1-4 hours)

### Scenario 5: Data Corruption / Ransomware
**Probability:** Low  
**Impact:** Critical  
**Recovery:** Restore from backup (1-4 hours)

### Scenario 6: DDoS Attack
**Probability:** Medium  
**Impact:** Medium  
**Recovery:** Activate AWS Shield Advanced + WAF (15-30 minutes)

---

## Recovery Procedures

### 1. EKS Cluster Recovery

```bash
# 1. Verify cluster health
kubectl get nodes
kubectl get pods -n astrovox

# 2. If unrecoverable, redeploy using Terraform
cd terraform/environments/production
terraform init
terraform apply -var="cluster_name=astrovox-prod-recovery"

# 3. Re-apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ -n astrovox

# 4. Verify deployment
kubectl rollout status deployment/astrovox-backend -n astrovox
kubectl rollout status deployment/astrovox-frontend -n astrovox
```

### 2. RDS Database Recovery

```bash
# 1. Check RDS status
aws rds describe-db-instances --db-instance-identifier astrovox-prod-postgres

# 2. If primary is down, promote read replica
aws rds promote-read-replica --db-instance-identifier astrovox-prod-postgres-replica

# 3. Update connection strings
kubectl set env deployment/astrovox-backend -n astrovox \
  DATABASE_URL=<new-connection-string>

# 4. Verify connectivity
kubectl exec -it deployment/astrovox-backend -n astrovox -- \
  python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')"
```

### 3. Redis Cache Recovery

```bash
# 1. Check cluster health
aws elasticache describe-replication-groups \
  --replication-group-id astrovox-prod-redis

# 2. If primary node failed, failover to replica
aws elasticache test-failover --replication-group-id astrovox-prod-redis

# 3. Verify connectivity
redis-cli -h <redis-endpoint> ping
```

### 4. Complete Region Failover

```bash
# 1. Update DNS records to point to DR region
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"astrovox.ai","Type":"A","AliasTarget":{"HostedZoneId":"Z987654321","DNSName":"dr-astrovox-alb.us-west-2.elb.amazonaws.com","EvaluateTargetHealth":false}}}]}'

# 2. Update application configuration
kubectl set env deployment/astrovox-backend -n astrovox \
  AWS_REGION=us-west-2 \
  DATABASE_URL=<dr-database-url> \
  REDIS_URL=<dr-redis-url>

# 3. Verify services in DR region
curl https://astrovox.ai/health
curl https://api.astrovox.ai/health
```

---

## Backup & Restore

### Automated Backups

| Component | Backup Method | Frequency | Retention |
|-----------|--------------|-----------|-----------|
| PostgreSQL | RDS automated backups + pg_dump to S3 | Continuous + Daily | 14 days (RDS), 30 days (S3) |
| Redis | ElastiCache snapshots | Daily | 7 days |
| Kubernetes | Velero backups | Daily | 30 days |
| S3 | Cross-region replication | Continuous | 30 days |

### Manual Backup Procedure

```bash
# Database backup
./scripts/backup-db.sh ./backups/manual

# Redis backup
./scripts/backup-redis.sh ./backups/manual

# Kubernetes resources
velero backup create manual-backup-$(date +%Y%m%d) \
  --include-namespaces astrovox \
  --wait

# Upload to S3
aws s3 sync ./backups/manual s3://astrovox-backups/manual/$(date +%Y%m%d)/
```

### Restore Procedure

```bash
# Restore database from S3 backup
aws s3 cp s3://astrovox-backups/2026-09-24/astrovox_20260924_120000.sql.gz - | \
  gunzip | psql -U astrovox -h <db-host> astrovox

# Restore Redis
redis-cli -h <redis-host> FLUSHALL
aws s3 cp s3://astrovox-backups/2026-09-24/redis_20260924_120000.rdb - | \
  redis-cli -h <redis-host> --pipe

# Restore Kubernetes
velero restore create --from-backup manual-backup-20260924
```

---

## Testing & Drills

### Quarterly DR Drill Checklist

- [ ] **Tabletop Exercise:** Review scenarios with team
- [ ] **Backup Verification:** Restore database from backup in isolated environment
- [ ] **Failover Test:** Test RDS failover to read replica
- [ ] **Region Failover:** Test DNS failover to DR region
- [ ] **Communication Test:** Verify alerting and on-call procedures
- [ ] **Documentation Review:** Update this document with findings

### Drill Schedule

| Drill Type | Frequency | Last Conducted | Next Scheduled |
|------------|-----------|----------------|----------------|
| Backup Restore | Quarterly | 2026-09-01 | 2026-12-01 |
| RDS Failover | Quarterly | 2026-09-01 | 2026-12-01 |
| Region Failover | Semi-annually | 2026-06-01 | 2026-12-01 |
| Full DR Simulation | Annually | 2026-01-15 | 2027-01-15 |

---

## Communication Plan

### Incident Severity Levels

| Severity | Description | Response Time | Escalation |
|----------|-------------|---------------|------------|
| **SEV1** | Complete outage, data loss | 15 minutes | VP Engineering |
| **SEV2** | Major degradation, partial outage | 30 minutes | Engineering Lead |
| **SEV3** | Minor issue, workaround available | 2 hours | On-call Engineer |
| **SEV4** | Cosmetic, no user impact | Next business day | Ticket |

### Communication Channels

- **Primary:** PagerDuty
- **Secondary:** Slack #incidents
- **Tertiary:** Email on-call@astrovox.ai
- **Customer Status:** status.astrovox.ai

### Status Page Updates

| Incident Stage | Update Time | Content |
|----------------|-------------|---------|
| Detected | Within 15 min | "We are investigating reports of..." |
| Identified | Within 30 min | "We have identified the issue..." |
| Monitoring | Every 30 min | "We are continuing to monitor..." |
| Resolved | Within 15 min of fix | "The issue has been resolved..." |

---

## Appendix

### Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| DevOps Lead | TBD | on-call@astrovox.ai |
| Engineering Lead | TBD | engineering@astrovox.ai |
| AWS Support | - | AWS Console |
| Database Admin | TBD | dba@astrovox.ai |

### Key AWS Resources

| Resource | Primary ARN | DR ARN |
|----------|-------------|--------|
| EKS Cluster | arn:aws:eks:us-east-1:123456789:cluster/astrovox-prod | arn:aws:eks:us-west-2:123456789:cluster/astrovox-prod |
| RDS Instance | arn:aws:rds:us-east-1:123456789:db:astrovox-prod-postgres | arn:aws:rds:us-west-2:123456789:db:astrovox-prod-postgres |
| Redis Cluster | arn:aws:elasticache:us-east-1:123456789:cluster:astrovox-prod-redis | arn:aws:elasticache:us-west-2:123456789:cluster:astrovox-prod-redis |
| S3 Bucket | arn:aws:s3:::astrovox-backups | arn:aws:s3:::astrovox-backups-dr |
