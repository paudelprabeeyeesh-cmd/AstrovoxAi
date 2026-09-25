#!/bin/bash
set -euo pipefail

BACKUP_FILE=${1:-./backups/redis/redis_latest.rdb.gz}
RESTORE_DIR=${RESTORE_DIR:-./restore/redis}

mkdir -p "$RESTORE_DIR"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

gunzip -c "$BACKUP_FILE" > "$RESTORE_DIR/dump.rdb"
echo "Redis backup extracted to: $RESTORE_DIR/dump.rdb"
echo "To restore:"
echo "  1. Stop Redis"
echo "  2. cp $RESTORE_DIR/dump.rdb <redis-data-dir>/dump.rdb"
echo "  3. Start Redis"
