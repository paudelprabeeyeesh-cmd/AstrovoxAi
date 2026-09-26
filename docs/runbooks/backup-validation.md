# AstrovoxAI Backup Validation Runbook

## Overview

This runbook provides procedures for validating backups to ensure data integrity and restore readiness.

## Validation Criteria

A backup is considered valid when:

1. The archive file exists and matches expected size.
2. The SHA-256 checksum matches the recorded value.
3. The archive can be opened and listed without errors.
4. A sample restore completes successfully.
5. Application smoke tests pass after restore.

## Automated Validation

```python
from app.reliability.backup import BackupValidator

validator = BackupValidator()
result = validator.validate_latest()
if not result.success:
    alert_on_call_engineer(result.error)
```

Expected output:

```json
{
  "path": "/tmp/astrovox_backups/backup_20240901T120000Z.tar.gz",
  "size_bytes": 10485760,
  "checksum": "abc123...",
  "validated": true,
  "validation_error": null
}
```

## Manual Validation

### 1. Verify File Existence

```bash
ls -lh /tmp/astrovox_backups/
```

### 2. Verify Checksum

```bash
sha256sum /tmp/astrovox_backups/backup_20240901T120000Z.tar.gz
```

Compare against stored checksum.

### 3. Verify Archive Integrity

```bash
tar -tzf /tmp/astrovox_backups/backup_20240901T120000Z.tar.gz | head -20
```

### 4. Test Restore

```bash
# Restore to temporary directory
mkdir /tmp/restore-test
tar -xzf /tmp/astrovox_backups/backup_20240901T120000Z.tar.gz -C /tmp/restore-test

# Run smoke tests against restored data
python -m app.tests.smoke --data-dir /tmp/restore-test
```

## Scheduling

| Backup Type | Frequency | Retention |
|-------------|-----------|-----------|
| Database | Hourly | 7 days |
| Object storage | Daily | 30 days |
| Full system | Weekly | 90 days |

## Troubleshooting

### Corrupt Backup

- Re-run backup job immediately.
- Verify storage health and disk space.
- Check for interrupted backup processes.

### Checksum Mismatch

- Re-download from remote storage.
- Verify network integrity.
- Re-run backup with retry.

### Restore Failure

- Check storage permissions.
- Verify target environment configuration.
- Review application compatibility with restored data version.
