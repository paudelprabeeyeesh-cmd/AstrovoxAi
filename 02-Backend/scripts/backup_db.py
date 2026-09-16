import os
import sys
import logging
import argparse
import subprocess
import glob
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def rotate_backups(backup_dir: str, keep_days: int = 7) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - (keep_days * 24 * 3600)
    for f in glob.glob(os.path.join(backup_dir, "astrovox_backup_*.sql.gz")):
        if os.path.getmtime(f) < cutoff:
            os.remove(f)
            logger.info(f"Removed old backup: {f}")


def backup_postgres(dry_run: bool = False) -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not set")
    
    backup_dir = os.getenv("BACKUP_DIR", "/tmp/backups")
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
    except Exception as e:
        logger.error(f"PostgreSQL backup failed: {e}")
        if os.path.exists(backup_file):
            os.remove(backup_file)
        raise


def main():
    parser = argparse.ArgumentParser(description="Database backup tool")
    parser.add_argument("--dry-run", action="store_true", help="Simulate backup without creating files")
    args = parser.parse_args()
    
    try:
        backup_postgres(dry_run=args.dry_run)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
