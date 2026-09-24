#!/bin/bash
set -euo pipefail

# AstrovoxAI Enhanced Backup Script
# Usage: ./scripts/backup-enhanced.sh [backup-type]
# Types: full, incremental, verify

BACKUP_TYPE="${1:-full}"
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="astrovox-backups"
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"

echo "=========================================="
echo "AstrovoxAI Backup: ${BACKUP_TYPE}"
echo "=========================================="

# Database Backup
if [ "${BACKUP_TYPE}" == "full" ] || [ "${BACKUP_TYPE}" == "incremental" ]; then
  echo "Backing up PostgreSQL..."
  DB_BACKUP="${BACKUP_DIR}/postgres_${DATE}.sql.gz"

  if docker compose ps postgres > /dev/null 2>&1; then
    docker compose exec -T postgres pg_dump -U astrovox --format=custom --compress=9 astrovox > "${DB_BACKUP}"
  elif command -v pg_dump > /dev/null 2>&1; then
    pg_dump -U astrovox --format=custom --compress=9 astrovox > "${DB_BACKUP}"
  else
    echo "Error: pg_dump not available"
    exit 1
  fi

  echo "✓ PostgreSQL backup: ${DB_BACKUP}"
  echo "  Size: $(du -h "${DB_BACKUP}" | cut -f1)"

  # Upload to S3
  aws s3 cp "${DB_BACKUP}" "s3://${S3_BUCKET}/postgres/${BACKUP_TYPE}/" --storage-class STANDARD_IA
  echo "✓ Uploaded to S3"
fi

# Redis Backup
if [ "${BACKUP_TYPE}" == "full" ]; then
  echo "Backing up Redis..."
  REDIS_BACKUP="${BACKUP_DIR}/redis_${DATE}.rdb"

  if docker compose ps redis > /dev/null 2>&1; then
    docker compose exec -T redis redis-cli BGSAVE
    docker compose cp redis:/data/dump.rdb "${REDIS_BACKUP}"
  elif command -v redis-cli > /dev/null 2>&1; then
    redis-cli BGSAVE
    cp /var/lib/redis/dump.rdb "${REDIS_BACKUP}"
  else
    echo "Error: redis-cli not available"
    exit 1
  fi

  echo "✓ Redis backup: ${REDIS_BACKUP}"
  echo "  Size: $(du -h "${REDIS_BACKUP}" | cut -f1)"
fi

# Kubernetes Resources
if [ "${BACKUP_TYPE}" == "full" ]; then
  echo "Backing up Kubernetes resources..."
  K8S_BACKUP="${BACKUP_DIR}/k8s_${DATE}.yaml"

  kubectl get all,configmaps,secrets,ingresses,serviceaccounts,roles,rolebindings,networkpolicies -n astrovox -o yaml > "${K8S_BACKUP}"
  echo "✓ Kubernetes backup: ${K8S_BACKUP}"
fi

# Verify backup
if [ "${BACKUP_TYPE}" == "verify" ]; then
  echo "Verifying backups..."
  for backup in "${BACKUP_DIR}"/*.sql.gz; do
    if [ -f "${backup}" ]; then
      if gunzip -t "${backup}" > /dev/null 2>&1; then
        echo "✓ ${backup} is valid"
      else
        echo "✗ ${backup} is CORRUPT"
      fi
    fi
  done
fi

# Cleanup old backups
echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}" -type f -mtime +${RETENTION_DAYS} -delete
echo "✓ Cleanup complete"

echo ""
echo "=========================================="
echo "Backup Complete"
echo "=========================================="
