"""Backup creation and validation."""
import hashlib
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class BackupResult:
    path: str
    size_bytes: int
    checksum: str
    created_at: str
    validated: bool
    validation_error: Optional[str] = None


class BackupValidator:
    def __init__(self, backup_dir: str = "/tmp/astrovox_backups"):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def create_backup(self, source_dirs: list[str], name: Optional[str] = None) -> BackupResult:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_name = name or f"backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, f"{backup_name}.tar.gz")
        checksum = hashlib.sha256()
        size = 0
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            with tarfile.open(fileobj=tmp, mode="w:gz") as tar:
                for src in source_dirs:
                    if os.path.exists(src):
                        tar.add(src, arcname=os.path.basename(src))
            size = tmp.tell()
            with open(tmp.name, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    checksum.update(chunk)
            shutil.move(tmp.name, backup_path)
        return BackupResult(
            path=backup_path,
            size_bytes=size,
            checksum=checksum.hexdigest(),
            created_at=datetime.now(timezone.utc).isoformat(),
            validated=False,
        )

    def validate_backup(self, result: BackupResult) -> BackupResult:
        if not os.path.exists(result.path):
            return BackupResult(
                path=result.path,
                size_bytes=result.size_bytes,
                checksum=result.checksum,
                created_at=result.created_at,
                validated=False,
                validation_error="Backup file not found",
            )
        expected = result.size_bytes
        actual = os.path.getsize(result.path)
        if actual != expected:
            return BackupResult(
                path=result.path,
                size_bytes=actual,
                checksum=result.checksum,
                created_at=result.created_at,
                validated=False,
                validation_error=f"Size mismatch: expected {expected}, got {actual}",
            )
        checksum = hashlib.sha256()
        with open(result.path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                checksum.update(chunk)
        if checksum.hexdigest() != result.checksum:
            return BackupResult(
                path=result.path,
                size_bytes=actual,
                checksum=checksum.hexdigest(),
                created_at=result.created_at,
                validated=False,
                validation_error="Checksum mismatch",
            )
        try:
            with tarfile.open(result.path, "r:gz") as tar:
                tar.getnames()
        except Exception as exc:
            return BackupResult(
                path=result.path,
                size_bytes=actual,
                checksum=checksum.hexdigest(),
                created_at=result.created_at,
                validated=False,
                validation_error=f"Corrupt archive: {exc}",
            )
        return BackupResult(
            path=result.path,
            size_bytes=actual,
            checksum=checksum.hexdigest(),
            created_at=result.created_at,
            validated=True,
        )
