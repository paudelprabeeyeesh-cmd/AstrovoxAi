#!/bin/bash
set -euo pipefail

NAMESPACE=${1:-astrovox}
POD=${2:-postgres-0}
BACKUP_DIR=${3:-./backups}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
kubectl exec -n $NAMESPACE $POD -- pg_dump -U astrovox astrovox > $BACKUP_DIR/astrovox_$TIMESTAMP.sql
gzip $BACKUP_DIR/astrovox_$TIMESTAMP.sql

echo "Backup saved to $BACKUP_DIR/astrovox_$TIMESTAMP.sql.gz"
