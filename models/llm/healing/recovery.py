import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, List, Mapping, Optional, Sequence

logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class Checkpoint:
    path: Path
    created_at: str
    metadata: Mapping[str, Any]
    size_bytes: int = 0

    def __post_init__(self) -> None:
        if self.size_bytes == 0 and self.path.exists():
            self.size_bytes = self.path.stat().st_size


@dataclass
class RecoveryResult:
    status: RecoveryStatus
    action: str
    started_at: str
    finished_at: str
    output: Mapping[str, Any]
    duration_ms: float = 0.0
    error: Optional[str] = None


CheckpointHandler = Callable[[], Checkpoint]
Restarter = Callable[[], bool]


class Recovery:
    def __init__(self, *, max_attempts: int = 3) -> None:
        self.max_attempts = max_attempts
        self._attempts: Mapping[str, int] = {}
        self._checkpoints: List[Checkpoint] = []

    def register_checkpoint(self, checkpoint: Checkpoint) -> None:
        self._checkpoints.append(checkpoint)

    def restore_checkpoint(self, checkpoint: Checkpoint) -> bool:
        if not checkpoint.path.exists():
            logger.error("Checkpoint not found: %s", checkpoint.path)
            return False
        logger.info("Restoring checkpoint: %s", checkpoint.path)
        return True

    def restart_process(
        self,
        command: Sequence[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> RecoveryResult:
        started = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        action = f"restart_process({' '.join(command)})"

        try:
            proc = subprocess.run(
                command,
                cwd=cwd,
                env=dict(env or {}),
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            finished = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            success = proc.returncode == 0
            status = RecoveryStatus.SUCCESS if success else RecoveryStatus.FAILED
            return RecoveryResult(
                status=status,
                action=action,
                started_at=started,
                finished_at=finished,
                output={
                    "returncode": proc.returncode,
                    "stdout": proc.stdout[:4000],
                    "stderr": proc.stderr[:4000],
                },
            )
        except Exception as exc:
            finished = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                action=action,
                started_at=started,
                finished_at=finished,
                output={},
                error=str(exc),
            )

    def cleanup_resources(self, paths: Sequence[Path]) -> RecoveryResult:
        started = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        removed: List[str] = []
        failed: List[str] = []
        for path in paths:
            try:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                    removed.append(str(path))
                elif path.is_file():
                    path.unlink(missing_ok=True)
                    removed.append(str(path))
                else:
                    failed.append(f"{path}: path does not exist")
            except Exception as exc:
                failed.append(f"{path}: {exc}")

        finished = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        status = RecoveryStatus.FAILED if failed and not removed else RecoveryStatus.SUCCESS
        return RecoveryResult(
            status=status,
            action="cleanup_resources",
            started_at=started,
            finished_at=finished,
            output={
                "removed": removed,
                "failed": failed,
            },
        )

    def attempt_recovery(
        self,
        result: Any,
        *,
        checkpoint: Optional[Checkpoint] = None,
    ) -> RecoveryResult:
        key = getattr(result, "action", "unknown")
        count = self._attempts.get(key, 0) + 1
        self._attempts[key] = count

        if count > self.max_attempts:
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                action=key,
                started_at=datetime.utcnow().isoformat(timespec="milliseconds"),
                finished_at=datetime.utcnow().isoformat(timespec="milliseconds"),
                output={},
                error="max attempts exceeded",
            )

        if checkpoint is not None:
            restored = self.restore_checkpoint(checkpoint)
            if not restored:
                return RecoveryResult(
                    status=RecoveryStatus.FAILED,
                    action="restore_checkpoint",
                    started_at=datetime.utcnow().isoformat(timespec="milliseconds"),
                    finished_at=datetime.utcnow().isoformat(timespec="milliseconds"),
                    output={},
                    error="checkpoint restoration failed",
                )

        return RecoveryResult(
            status=RecoveryStatus.SUCCESS,
            action=key,
            started_at=datetime.utcnow().isoformat(timespec="milliseconds"),
            finished_at=datetime.utcnow().isoformat(timespec="milliseconds"),
            output={"attempt": count},
        )
