#!/bin/bash
set -euo pipefail

# AstrovoxAI S3 Backup Upload Script
# Usage: ./scripts/backup-s3.sh [local-dir]

LOCAL_DIR="${1:-./backups}"
S3_BUCKET="astrovox-backups"
RETENTION_DAYS=30
LIFECYCLE_TRANSITION_DAYS=7

echo "=========================================="
echo "AstrovoxAI S3 Backup Upload"
echo "=========================================="

if [ ! -d "${LOCAL_DIR}" ]; then
  echo "Error: Directory ${LOCAL_DIR} does not exist"
  exit 1
fi

# Upload to S3 with server-side encryption
aws s3 sync "${LOCAL_DIR}" "s3://${S3_BUCKET}/manual/" \
  --storage-class STANDARD_IA \
  --sse AES256 \
  --exclude "*.tmp"

echo "✓ Uploaded to s3://${S3_BUCKET}/manual/"

# Apply lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket "${S3_BUCKET}" \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "BackupLifecycle",
        "Status": "Enabled",
        "Filter": {
          "Prefix": "manual/"
        },
        "Transitions": [
          {
            "Days": 7,
            "StorageClass": "GLACIER"
          },
          {
            "Days": 30,
            "StorageClass": "DEEP_ARCHIVE"
          }
        ],
        "Expiration": {
          "Days": 90
        }
      }
    ]
  }'

echo "✓ Lifecycle policy applied"
echo "  - 7 days: Glacier"
echo "  - 30 days: Deep Archive"
echo "  - 90 days: Deleted"

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket "${S3_BUCKET}" \
  --versioning-configuration Status=Enabled

echo "✓ Versioning enabled"

# Enable replication to DR region
aws s3api put-bucket-replication \
  --bucket "${S3_BUCKET}" \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456789012:role/s3-replication-role",
    "Rules": [
      {
        "Status": "Enabled",
        "Priority": 1,
        "Filter": {
          "Prefix": ""
        },
        "Destination": {
          "Bucket": "arn:aws:s3:::astrovox-backups-dr",
          "StorageClass": "STANDARD"
        }
      }
    ]
  }'

echo "✓ Cross-region replication enabled"
echo ""
echo "Backup upload complete"
