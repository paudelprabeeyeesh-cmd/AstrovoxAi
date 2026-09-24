#!/bin/bash
set -euo pipefail

# AstrovoxAI Database Restore Script
# Usage: ./scripts/restore-db.sh <backup-file>

if [ -z "${1:-}" ]; then
  echo "Usage: $0 <backup-file>"
  echo "Example: $0 ./backups/postgres/astrovox_20240101_120000.sql.gz"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "Restoring database from $BACKUP_FILE..."
echo "WARNING: This will overwrite existing data!"

read -p "Are you sure? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Restore cancelled"
  exit 0
fi

# Check if running in Docker or locally
if docker compose ps postgres > /dev/null 2>&1; then
  gunzip < "$BACKUP_FILE" | docker compose exec -T postgres psql -U astrovox astrovox
elif command -v psql > /dev/null 2>&1; then
  gunzip < "$BACKUP_FILE" | psql -U astrovox astrovox
else
  echo "Error: Neither Docker nor psql found"
  exit 1
fi

echo "Restore complete!"
