#!/bin/bash
set -euo pipefail

REDIS_URL=${REDIS_URL:-redis://localhost:6379}
BACKUP_DIR=${BACKUP_DIR:-./backups/redis}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/redis_$TIMESTAMP.rdb"
RETENTION_DAYS=${RETENTION_DAYS:-3}

mkdir -p "$BACKUP_DIR"

redis-cli -u "$REDIS_URL" BGSAVE
sleep 1

REDIS_HOST=$(echo "$REDIS_URL" | sed -E "s/redis:\/\/([^:@]+)(:[^@]+)?@(.+)/\3/")
REDIS_DIR=$(redis-cli -u "$REDIS_URL" CONFIG GET dir | tail -1)

if [ -n "$REDIS_DIR" ]; then
    RDB_FILE="$REDIS_DIR/dump.rdb"
else
    RDB_FILE="/data/dump.rdb"
fi

if [ -f "$RDB_FILE" ]; then
    cp "$RDB_FILE" "$BACKUP_FILE"
    gzip "$BACKUP_FILE"
    echo "Redis backup saved: ${BACKUP_FILE}.gz"
else
    echo "ERROR: Redis dump not found at $RDB_FILE"
    exit 1
fi

find "$BACKUP_DIR" -name "redis_*.rdb.gz" -mtime +$RETENTION_DAYS -delete
echo "Redis backup complete"
