"""Checkpoint management for training."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Checkpoint:
    """A training checkpoint."""
    id: str
    step: int
    epoch: int
    path: str
    metrics: dict = field(default_factory=dict)
    created: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        return {"id": self.id, "step": self.step, "epoch": self.epoch, "path": self.path,
                "metrics": self.metrics}


class CheckpointManager:
    """Save, load, and manage checkpoints."""

    def __init__(self, save_dir: str = "checkpoints", keep_last: int = 5):
        self.save_dir = save_dir
        self.keep_last = keep_last
        self.checkpoints: dict[str, Checkpoint] = {}

    def save(self, step: int, epoch: int, state: dict, metrics: dict | None = None) -> Checkpoint:
        ckpt = Checkpoint(id=f"ckpt_{step}", step=step, epoch=epoch,
                          path=f"{self.save_dir}/step_{step}.pt", metrics=dict(metrics or {}))
        self.checkpoints[ckpt.id] = ckpt
        self._prune()
        return ckpt

    def _prune(self) -> None:
        kept = sorted(self.checkpoints.values(), key=lambda c: c.step)[-self.keep_last:]
        to_remove = [c.id for c in self.checkpoints.values() if c not in kept]
        for rid in to_remove:
            del self.checkpoints[rid]

    def load(self, ckpt_id: str) -> Checkpoint | None:
        return self.checkpoints.get(ckpt_id)

    def load_latest(self) -> Checkpoint | None:
        if not self.checkpoints:
            return None
        return max(self.checkpoints.values(), key=lambda c: c.step)

    def delete(self, ckpt_id: str) -> bool:
        if ckpt_id in self.checkpoints:
            del self.checkpoints[ckpt_id]
            return True
        return False

    def list_checkpoints(self) -> list[Checkpoint]:
        return list(self.checkpoints.values())

    def count(self) -> int:
        return len(self.checkpoints)
