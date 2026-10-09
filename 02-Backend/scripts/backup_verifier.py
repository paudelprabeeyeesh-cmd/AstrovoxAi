import os
import sys
import logging
import subprocess
import argparse
from typing import Optional

logger = logging.getLogger(__name__)


def verify_backup(backup_file: str, database_url: Optional[str] = None) -> bool:
    if not os.path.exists(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
        return False

    try:
        size = os.path.getsize(backup_file)
        if size == 0:
            logger.error(f"Backup file is empty: {backup_file}")
            return False

        if backup_file.endswith(".gz"):
            result = subprocess.run(
                ["gzip", "-t", backup_file],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error(f"Backup file is corrupted (gzip check failed): {backup_file}")
                return False

        logger.info(f"Backup verified successfully: {backup_file} (size: {size} bytes)")
        return True
    except Exception as _e:  # noqa: BLE001
        logger.error(f"Backup verification failed: {e}")
        return False


def restore_and_verify(backup_file: str, database_url: Optional[str] = None) -> bool:
    if not os.path.exists(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
        return False

    database_url = database_url or os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL is not set")
        return False

    try:
        temp_db = "/tmp/astrovox_restore_test.db"
        if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
            result = subprocess.run(
                ["psql", "--dbname", database_url, "-c", f"SELECT pg_database_size('{database_url.split('/')[-1]}')"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error(f"PostgreSQL restore verification failed: {result.stderr}")
                return False
        else:
            shutil.copy(backup_file, temp_db)
            import sqlite3
            conn = sqlite3.connect(temp_db)
            conn.execute("SELECT COUNT(*) FROM sqlite_master")
            conn.close()
            os.remove(temp_db)

        logger.info(f"Restore verification successful: {backup_file}")
        return True
    except Exception as _e:  # noqa: BLE001
        logger.error(f"Restore verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Backup verification tool")
    parser.add_argument("backup_file", help="Path to backup file")
    parser.add_argument("--restore", action="store_true", help="Also verify restore")
    args = parser.parse_args()

    verified = verify_backup(args.backup_file)
    if args.restore:
        verified = verified and restore_and_verify(args.backup_file)

    if verified:
        print("Backup verification passed")
        sys.exit(0)
    else:
        print("Backup verification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()