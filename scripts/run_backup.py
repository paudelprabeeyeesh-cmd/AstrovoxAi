import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backup_recovery.backup_service import DatabaseBackupService


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    service = DatabaseBackupService()
    manifests = service.run_full_backup()
    if not manifests:
        logging.warning("No backups completed")
        return 1
    logging.info("Backups completed: %s", [str(m.path) for m in manifests])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
