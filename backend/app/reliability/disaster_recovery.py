"""Disaster recovery drill execution and tracking."""
import os
import random
import string
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .backup import BackupValidator, BackupResult


@dataclass
class DrillResult:
    name: str
    started_at: str
    finished_at: Optional[str]
    duration_seconds: float
    restored_successfully: bool
    validation_error: Optional[str]


class DisasterRecoveryDrill:
    def __init__(self, backup_validator: Optional[BackupValidator] = None):
        self.backup_validator = backup_validator or BackupValidator()
        self.results: list[DrillResult] = []

    def run_drill(self, source_dirs: list[str], restore_dir: Optional[str] = None) -> DrillResult:
        started = datetime.now(timezone.utc)
        name = f"drill_{started.strftime('%Y%m%dT%H%M%SZ')}"
        validation_error = None
        restored_successfully = False
        try:
            backup = self.backup_validator.create_backup(source_dirs, name=name)
            validated = self.backup_validator.validate_backup(backup)
            if not validated.validation_error and restore_dir:
                target = restore_dir or tempfile.mkdtemp(prefix="drill_restore_")
                os.makedirs(target, exist_ok=True)
                with tarfile.open(validated.path, "r:gz") as tar:
                    tar.extractall(target)
                restored_successfully = True
        except Exception as exc:
            validation_error = str(exc)
        finished = datetime.now(timezone.utc)
        result = DrillResult(
            name=name,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            duration_seconds=(finished - started).total_seconds(),
            restored_successfully=restored_successfully,
            validation_error=validation_error,
        )
        self.results.append(result)
        return result

    def last_result(self) -> Optional[DrillResult]:
        return self.results[-1] if self.results else None
