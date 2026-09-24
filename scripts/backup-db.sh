#!/bin/bash
set -euo pipefail

# AstrovoxAI Database Backup Script
# Usage: ./scripts/backup-db.sh [output-dir]

OUTPUT_DIR="${1:-./backups/postgres}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$OUTPUT_DIR/astrovox_$DATE.sql.gz"

mkdir -p "$OUTPUT_DIR"

echo "Backing up database to $BACKUP_FILE..."

# Check if running in Docker or locally
if docker compose ps postgres > /dev/null 2>&1; then
  docker compose exec -T postgres pg_dump -U astrovox astrovox | gzip > "$BACKUP_FILE"
elif command -v pg_dump > /dev/null 2>&1; then
  pg_dump -U astrovox astrovox | gzip > "$BACKUP_FILE"
else
  echo "Error: Neither Docker nor pg_dump found"
  exit 1
fi

echo "Backup complete: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"

# Keep only last 30 backups
ls -t "$OUTPUT_DIR"/astrovox_*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm --

echo "Old backups cleaned up (keeping last 30)"
