import os
import sys
import logging
import argparse
import subprocess
import glob
import sqlite3
import shutil
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def rotate_backups(backup_dir: str, keep_days: int = 7) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - (keep_days * 24 * 3600)
    for f in glob.glob(os.path.join(backup_dir, "astrovox_backup_*")):
        if os.path.getmtime(f) < cutoff:
            os.remove(f)
            logger.info(f"Removed old backup: {f}")


def backup_postgres(dry_run: bool = False) -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not set")

    backup_dir = os.environ.get("BACKUP_DIR", "/tmp/backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"astrovox_backup_{timestamp}.sql.gz")

    if dry_run:
        logger.info(f"[DRY RUN] Would create PostgreSQL backup: {backup_file}")
        return backup_file

    rotate_backups(backup_dir)

    try:
        with open(backup_file, "wb") as f:
            pg_dump = subprocess.Popen(
                ["pg_dump", "--dbname", database_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            gzip = subprocess.Popen(
                ["gzip", "-c"],
                stdin=pg_dump.stdout,
                stdout=f,
                stderr=subprocess.PIPE,
            )
            pg_dump.stdout.close()
            _, gzip_err = gzip.communicate()
            _, pg_err = pg_dump.communicate()

            if pg_dump.returncode != 0:
                raise RuntimeError(f"pg_dump failed with code {pg_dump.returncode}: {pg_err.decode()}")
            if gzip.returncode != 0:
                raise RuntimeError(f"gzip failed with code {gzip.returncode}: {gzip_err.decode()}")

        size = os.path.getsize(backup_file)
        logger.info(f"PostgreSQL backup created at {backup_file} (size: {size} bytes, timestamp: {timestamp})")
        return backup_file
    except Exception as _e:  # noqa: BLE001
        logger.error(f"PostgreSQL backup failed: {_e}")
        if os.path.exists(backup_file):
            os.remove(backup_file)
        raise


def backup_sqlite(db_path: str, backup_dir: Optional[str] = None, dry_run: bool = False) -> str:
    if not db_path or not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    backup_dir = backup_dir or os.environ.get("BACKUP_DIR", "/tmp/backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(db_path)
    backup_file = os.path.join(backup_dir, f"astrovox_backup_{timestamp}_{base_name}")

    if dry_run:
        logger.info(f"[DRY RUN] Would create SQLite backup: {backup_file}")
        return backup_file

    rotate_backups(backup_dir)

    try:
        shutil.copy2(db_path, backup_file)
        wal_path = db_path + "-wal"
        shm_path = db_path + "-shm"
        if os.path.exists(wal_path):
            shutil.copy2(wal_path, backup_file + "-wal")
        if os.path.exists(shm_path):
            shutil.copy2(shm_path, backup_file + "-shm")
        size = os.path.getsize(backup_file)
        logger.info(f"SQLite backup created at {backup_file} (size: {size} bytes)")
        return backup_file
    except Exception as _e:  # noqa: BLE001
        logger.error(f"SQLite backup failed: {_e}")
        if os.path.exists(backup_file):
            os.remove(backup_file)
        raise


def backup_database(dry_run: bool = False) -> str:
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        return backup_postgres(dry_run=dry_run)

    db_path = os.environ.get("ASTROVOX_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app.db"))
    return backup_sqlite(db_path, dry_run=dry_run)


def backup_to_s3() -> bool:
    try:
        import boto3
    except ImportError:
        logger.warning("boto3 not installed; skipping S3 backup")
        return False

    s3_bucket = os.environ.get("BACKUP_S3_BUCKET")
    if not s3_bucket:
        logger.info("BACKUP_S3_BUCKET not set; skipping S3 backup")
        return True

    try:
        backup_file = backup_database()
        s3_key = os.path.basename(backup_file)
        s3 = boto3.client("s3")
        s3.upload_file(backup_file, s3_bucket, s3_key)
        logger.info(f"S3 backup uploaded: s3://{s3_bucket}/{s3_key}")
        return True
    except Exception as _e:  # noqa: BLE001
        logger.error(f"S3 backup failed: {_e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Database backup tool")
    parser.add_argument("--dry-run", action="store_true", help="Simulate backup without creating files")
    args = parser.parse_args()

    try:
        backup_database(dry_run=args.dry_run)
        sys.exit(0)
    except Exception as _e:  # noqa: BLE001
        logger.error(f"Backup failed: {_e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
