import os
import boto3
import logging
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


def backup_database() -> str:
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"astrovox_backup_{timestamp}.sqlite")
    
    import shutil
    db_path = os.getenv("ASTROVOX_DB", "astrovox.db")
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_file)
        logger.info(f"Database backed up to {backup_file}")
        return backup_file
    return ""


def backup_to_s3() -> bool:
    try:
        s3 = boto3.client("s3")
        bucket = os.getenv("BACKUP_BUCKET", "astrovox-backups")
        backup_file = backup_database()
        
        if backup_file and os.path.exists(backup_file):
            s3.upload_file(
                backup_file,
                bucket,
                f"daily/{os.path.basename(backup_file)}"
            )
            logger.info(f"Backup uploaded to s3://{bucket}/daily/{os.path.basename(backup_file)}")
            return True
    except Exception as e:
        logger.error(f"S3 backup failed: {e}")
    return False


def restore_database(backup_file: str) -> bool:
    import shutil
    db_path = os.getenv("ASTROVOX_DB", "astrovox.db")
    try:
        shutil.copy2(backup_file, db_path)
        logger.info(f"Database restored from {backup_file}")
        return True
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False
