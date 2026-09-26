"""Fault recovery: checkpoint, restart, and resumable training."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class FaultRecoveryConfig:
    checkpoint_dir: str = "/tmp/astrovox_recovery"
    max_checkpoints: int = 5
    auto_checkpoint_interval: int = 500
    resume_from_latest: bool = True


class FaultRecoveryManager:
    def __init__(self, config: FaultRecoveryConfig):
        self.config = config
        self.checkpoint_dir = config.checkpoint_dir
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self._recovery_log: List[Dict[str, Any]] = []

    def save_recovery_checkpoint(self, model: nn.Module, optimizer: torch.optim.Optimizer, step: int, epoch: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"recovery_epoch{epoch}_step{step}_{timestamp}.pt"
        path = os.path.join(self.checkpoint_dir, filename)
        ckpt = {"model": model.state_dict(), "optimizer": optimizer.state_dict(), "step": step, "epoch": epoch, "timestamp": timestamp}
        if metadata:
            ckpt.update(metadata)
        torch.save(ckpt, path)
        self._log_recovery_event("checkpoint_saved", {"path": path, "step": step, "epoch": epoch})
        self._prune_old_checkpoints()
        return path

    def load_recovery_checkpoint(self, model: nn.Module, optimizer: torch.optim.Optimizer, checkpoint_path: Optional[str] = None) -> Dict[str, Any]:
        if checkpoint_path is None:
            checkpoint_path = self._find_latest_checkpoint()
        if checkpoint_path is None or not os.path.exists(checkpoint_path):
            logger.warning("No recovery checkpoint found")
            return {"step": 0, "epoch": 0}
        ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        model.load_state_dict(ckpt["model"])
        optimizer.load_state_dict(ckpt["optimizer"])
        self._log_recovery_event("checkpoint_loaded", {"path": checkpoint_path, "step": ckpt["step"], "epoch": ckpt["epoch"]})
        return {"step": ckpt["step"], "epoch": ckpt["epoch"]}

    def _find_latest_checkpoint(self) -> Optional[str]:
        files = [f for f in os.listdir(self.checkpoint_dir) if f.startswith("recovery_") and f.endswith(".pt")]
        if not files:
            return None
        files.sort(reverse=True)
        return os.path.join(self.checkpoint_dir, files[0])

    def _prune_old_checkpoints(self) -> None:
        files = [os.path.join(self.checkpoint_dir, f) for f in os.listdir(self.checkpoint_dir) if f.startswith("recovery_") and f.endswith(".pt")]
        if len(files) > self.config.max_checkpoints:
            files.sort()
            for old in files[:-self.config.max_checkpoints]:
                os.remove(old)
                logger.debug("Pruned old checkpoint: %s", old)

    def handle_failure(self, model: nn.Module, optimizer: torch.optim.Optimizer, failure_step: int, failure_epoch: int) -> Dict[str, Any]:
        logger.error("Handling failure at step %d, epoch %d", failure_step, failure_epoch)
        recovery_path = self.save_recovery_checkpoint(model, optimizer, failure_step, failure_epoch, {"failure": True})
        state = self.load_recovery_checkpoint(model, optimizer)
        self._log_recovery_event("failure_recovered", {"failure_step": failure_step, "recovery_step": state["step"]})
        return state

    def _log_recovery_event(self, event: str, data: Dict[str, Any]) -> None:
        entry = {"event": event, "timestamp": datetime.utcnow().isoformat()}
        entry.update(data)
        self._recovery_log.append(entry)

    def get_recovery_log(self) -> List[Dict[str, Any]]:
        return self._recovery_log.copy()

    def list_checkpoints(self) -> List[str]:
        return sorted([os.path.join(self.checkpoint_dir, f) for f in os.listdir(self.checkpoint_dir) if f.startswith("recovery_") and f.endswith(".pt")])
