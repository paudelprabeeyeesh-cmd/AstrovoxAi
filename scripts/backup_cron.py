#!/usr/bin/env python3
"""Cron-compatible database backup runner."""
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

try:
    from backup_recovery.backup_service import DatabaseBackupService
except Exception as exc:  # noqa: BLE001
    logging.error("Failed to import backup service: %s", exc)
    sys.exit(1)

service = DatabaseBackupService()
manifests = service.run_full_backup()
if not manifests:
    logging.warning("No backups completed")
    sys.exit(1)
logging.info("Backups completed: %s", [str(m.path) for m in manifests])
