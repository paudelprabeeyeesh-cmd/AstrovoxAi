"""Storage management with S3 support and backup strategies."""

import os
import logging
import shutil
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class StorageConfig:
    """Storage configuration."""
    backend: str = "local"
    local_path: str = "./storage"
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_endpoint: str = ""
    max_file_size: int = 50 * 1024 * 1024
    allowed_extensions: list = None

    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = [
                ".txt", ".pdf", ".doc", ".docx", ".md",
                ".png", ".jpg", ".jpeg", ".gif", ".webp",
                ".py", ".js", ".ts", ".json", ".csv",
            ]


class StorageManager:
    """Unified storage manager with local and S3 backends."""

    def __init__(self, config: StorageConfig = None):
        self._config = config or StorageConfig()
        self._s3_client = None

    def _get_s3(self):
        """Get or create S3 client."""
        if self._s3_client is None and self._config.backend == "s3":
            try:
                import boto3
                self._s3_client = boto3.client(
                    "s3",
                    region_name=self._config.s3_region,
                    endpoint_url=self._config.s3_endpoint or None,
                )
            except ImportError:
                logger.warning("boto3 not installed, falling back to local storage")
                self._config.backend = "local"
        return self._s3_client

    def save_file(self, path: str, content: bytes) -> dict:
        """Save a file."""
        if len(content) > self._config.max_file_size:
            raise ValueError(f"File too large: {len(content)} bytes")

        ext = os.path.splitext(path)[1].lower()
        if ext not in self._config.allowed_extensions:
            raise ValueError(f"File type not allowed: {ext}")

        if self._config.backend == "s3":
            return self._save_to_s3(path, content)
        return self._save_to_local(path, content)

    def _save_to_local(self, path: str, content: bytes) -> dict:
        """Save file locally."""
        full_path = os.path.join(self._config.local_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(content)

        return {
            "backend": "local",
            "path": path,
            "size": len(content),
            "url": f"/storage/{path}",
        }

    def _save_to_s3(self, path: str, content: bytes) -> dict:
        """Save file to S3."""
        s3 = self._get_s3()
        if not s3:
            return self._save_to_local(path, content)

        s3.put_object(
            Bucket=self._config.s3_bucket,
            Key=path,
            Body=content,
        )

        return {
            "backend": "s3",
            "path": path,
            "size": len(content),
            "url": f"https://{self._config.s3_bucket}.s3.{self._config.s3_region}.amazonaws.com/{path}",
        }

    def get_file(self, path: str) -> Optional[bytes]:
        """Get a file."""
        if self._config.backend == "s3":
            return self._get_from_s3(path)
        return self._get_from_local(path)

    def _get_from_local(self, path: str) -> Optional[bytes]:
        """Get file from local storage."""
        full_path = os.path.join(self._config.local_path, path)
        if not os.path.exists(full_path):
            return None
        with open(full_path, "rb") as f:
            return f.read()

    def _get_from_s3(self, path: str) -> Optional[bytes]:
        """Get file from S3."""
        s3 = self._get_s3()
        if not s3:
            return None
        try:
            response = s3.get_object(Bucket=self._config.s3_bucket, Key=path)
            return response["Body"].read()
        except Exception:
            return None

    def delete_file(self, path: str) -> bool:
        """Delete a file."""
        if self._config.backend == "s3":
            return self._delete_from_s3(path)
        return self._delete_from_local(path)

    def _delete_from_local(self, path: str) -> bool:
        """Delete file from local storage."""
        full_path = os.path.join(self._config.local_path, path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    def _delete_from_s3(self, path: str) -> bool:
        """Delete file from S3."""
        s3 = self._get_s3()
        if not s3:
            return False
        try:
            s3.delete_object(Bucket=self._config.s3_bucket, Key=path)
            return True
        except Exception:
            return False


class BackupManager:
    """Manage automated backups."""

    def __init__(self, backup_dir: str = "./backups"):
        self._backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def create_backup(self, name: str, paths: list[str]) -> dict:
        """Create a backup."""
        import tarfile

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{timestamp}.tar.gz"
        backup_path = os.path.join(self._backup_dir, backup_name)

        with tarfile.open(backup_path, "w:gz") as tar:
            for path in paths:
                if os.path.exists(path):
                    tar.add(path, arcname=os.path.basename(path))

        size = os.path.getsize(backup_path)

        return {
            "name": backup_name,
            "path": backup_path,
            "size": size,
            "timestamp": timestamp,
        }

    def list_backups(self) -> list[dict]:
        """List all backups."""
        backups = []
        for filename in os.listdir(self._backup_dir):
            filepath = os.path.join(self._backup_dir, filename)
            stat = os.stat(filepath)
            backups.append({
                "name": filename,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        backups.sort(key=lambda b: b["created"], reverse=True)
        return backups

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """Remove backups older than keep_days."""
        cutoff = datetime.now() - timedelta(days=keep_days)
        removed = 0

        for filename in os.listdir(self._backup_dir):
            filepath = os.path.join(self._backup_dir, filename)
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                removed += 1

        return removed


storage_config = StorageConfig(
    backend=os.getenv("STORAGE_BACKEND", "local"),
    local_path=os.getenv("STORAGE_ROOT", "./storage"),
    s3_bucket=os.getenv("S3_BUCKET", ""),
    s3_region=os.getenv("S3_REGION", "us-east-1"),
)
storage_manager = StorageManager(storage_config)
backup_manager = BackupManager(os.getenv("BACKUP_DIR", "./backups"))
