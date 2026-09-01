#!/bin/bash
# AstrovoxAI Backup Script
# Usage: ./scripts/backup.sh

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

echo "Creating backup at $BACKUP_PATH..."

mkdir -p "$BACKUP_PATH"

# Backup environment config
if [ -f .env ]; then
    cp .env "$BACKUP_PATH/.env.backup"
    echo "Backed up .env"
fi

# Backup Docker volumes
if command -v docker >/dev/null 2>&1; then
    echo "Backing up Docker volumes..."
    docker run --rm -v astravox-ai_postgres_data:/data -v "$BACKUP_PATH:/backup" alpine tar czf /backup/postgres_data.tar.gz -C /data . 2>/dev/null || true
    docker run --rm -v astravox-ai_redis_data:/data -v "$BACKUP_PATH:/backup" alpine tar czf /backup/redis_data.tar.gz -C /data . 2>/dev/null || true
fi

# Backup storage
if [ -d storage ]; then
    tar czf "$BACKUP_PATH/storage.tar.gz" storage/
    echo "Backed up storage/"
fi

# Create manifest
cat > "$BACKUP_PATH/manifest.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "version": "2.0.0",
    "files": [
        ".env.backup",
        "postgres_data.tar.gz",
        "redis_data.tar.gz",
        "storage.tar.gz"
    ]
}
EOF

echo "Backup complete: $BACKUP_PATH"
echo "Size: $(du -sh "$BACKUP_PATH" | cut -f1)"
