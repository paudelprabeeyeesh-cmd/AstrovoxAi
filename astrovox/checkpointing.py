"""Fault recovery and checkpointing for distributed jobs.

Provides checkpoint serialization, automatic recovery from the latest usable
checkpoint, and basic job state tracking. The on-disk format is JSON plus
binary weight blobs, which is intentionally simple and portable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CheckpointMetadata:
    step: int
    epoch: int
    loss: float
    path: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class CheckpointManager:
    def __init__(self, directory: str = "checkpoints") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.directory / "registry.json"
        self._registry: Dict[str, CheckpointMetadata] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        if self._registry_path.exists():
            data = json.loads(self._registry_path.read_text(encoding="utf-8"))
            self._registry = {k: CheckpointMetadata(**v) for k, v in data.items()}

    def _save_registry(self) -> None:
        data = {k: {"step": v.step, "epoch": v.epoch, "loss": v.loss, "path": v.path, "created_at": v.created_at} for k, v in self._registry.items()}
        self._registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def save(self, step: int, epoch: int, loss: float, weights: Dict[str, Any]) -> str:
        name = f"ckpt_step{step}"
        path = self.directory / f"{name}.npz" if hasattr(weights, "save") else self.directory / f"{name}.json"
        if hasattr(weights, "save"):
            np.savez(path, **{k: np.asarray(v) for k, v in weights.items()})
        else:
            path.write_text(json.dumps(weights, default=str), encoding="utf-8")
        metadata = CheckpointMetadata(step=step, epoch=epoch, loss=loss, path=str(path))
        self._registry[name] = metadata
        self._save_registry()
        return name

    def latest(self) -> Optional[CheckpointMetadata]:
        if not self._registry:
            return None
        return max(self._registry.values(), key=lambda meta: meta.step)

    def recover(self) -> Optional[Dict[str, Any]]:
        meta = self.latest()
        if meta is None:
            return None
        path = Path(meta.path)
        if not path.exists():
            return None
        if path.suffix == ".npz":
            return dict(np.load(path))
        return json.loads(path.read_text(encoding="utf-8"))


class JobTracker:
    def __init__(self, manager: CheckpointManager) -> None:
        self.manager = manager
        self.state: Dict[str, Any] = {"status": "running"}

    def update(self, **kwargs: Any) -> None:
        self.state.update(kwargs)
        self._persist()

    def _persist(self) -> None:
        path = self.manager.directory / "job_state.json"
        path.write_text(json.dumps(self.state, default=str), encoding="utf-8")

    def fail(self, reason: str) -> None:
        self.state["status"] = "failed"
        self.state["failure_reason"] = reason
        self._persist()

    def resume(self) -> bool:
        path = self.manager.directory / "job_state.json"
        if not path.exists():
            return False
        self.state = json.loads(path.read_text(encoding="utf-8"))
        return self.state.get("status") == "running"
