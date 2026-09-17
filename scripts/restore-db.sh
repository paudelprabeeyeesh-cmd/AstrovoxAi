#!/bin/bash
set -euo pipefail

NAMESPACE=${1:-astrovox}
POD=${2:-postgres-0}
BACKUP_FILE=${3:?Usage: $0 <namespace> <pod> <backup_file>}

if [[ ! -f $BACKUP_FILE ]]; then
  echo "Error: Backup file $BACKUP_FILE not found"
  exit 1
fi

gunzip -c $BACKUP_FILE | kubectl exec -i -n $NAMESPACE $POD -- psql -U astrovox astrovox

echo "Restore complete."
