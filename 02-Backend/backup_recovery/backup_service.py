import logging
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BackupManifest:
    backup_id: str
    path: Path
    size_bytes: int
    created_at: str
    checksum: str
    status: str = "completed"


class DatabaseBackupService:
    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or Path(os.getenv("BACKUP_DIR", "backups/database"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def backup_postgres(self) -> Optional[BackupManifest]:
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "astrovox")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")

        backup_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"astrovox_{backup_id}.sql.gz"
        dest = self.output_dir / filename

        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password

        cmd = [
            "pg_dump",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", database,
            "-F", "c",
            "-f", str(dest),
        ]
        try:
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
            checksum = self._sha256(dest)
            size = dest.stat().st_size
            logger.info("PostgreSQL backup completed: %s", dest)
            return BackupManifest(
                backup_id=backup_id,
                path=dest,
                size_bytes=size,
                created_at=datetime.now(timezone.utc).isoformat(),
                checksum=checksum,
            )
        except FileNotFoundError:
            logger.error("pg_dump not found; skipping PostgreSQL backup")
            return None
        except subprocess.CalledProcessError as exc:
            logger.error("pg_dump failed: %s", exc.stderr)
            return None

    def backup_sqlite(self, db_path: str) -> Optional[BackupManifest]:
        src = Path(db_path)
        if not src.exists():
            logger.warning("SQLite database not found: %s", src)
            return None
        backup_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"sqlite_{backup_id}.sql.gz"
        dest = self.output_dir / filename
        try:
            import shutil
            import gzip
            with gzip.open(dest, "wb") as gz:
                with src.open("rb") as f:
                    shutil.copyfileobj(f, gz)
            checksum = self._sha256(dest)
            size = dest.stat().st_size
            logger.info("SQLite backup completed: %s", dest)
            return BackupManifest(
                backup_id=backup_id,
                path=dest,
                size_bytes=size,
                created_at=datetime.now(timezone.utc).isoformat(),
                checksum=checksum,
            )
        except Exception as exc:
            logger.error("SQLite backup failed: %s", exc)
            return None

    def run_full_backup(self) -> List[BackupManifest]:
        manifests = []
        pg = self.backup_postgres()
        if pg:
            manifests.append(pg)
        sqlite = self.backup_sqlite(os.getenv("ASTROVOX_DB_PATH", "app.db"))
        if sqlite:
            manifests.append(sqlite)
        self._rotate_backups()
        return manifests

    def _rotate_backups(self) -> None:
        max_backups = int(os.getenv("BACKUP_RETENTION_COUNT", "30"))
        files = sorted(self.output_dir.glob("*.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[max_backups:]:
            try:
                old.unlink()
                logger.info("Rotated old backup: %s", old)
            except Exception as exc:
                logger.error("Failed to rotate backup %s: %s", old, exc)

    @staticmethod
    def _sha256(path: Path) -> str:
        import hashlib
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
