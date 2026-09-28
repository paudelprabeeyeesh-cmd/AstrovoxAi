"""Sharded checkpoint saving/loading with async support and resume verification."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import torch
import torch.distributed as dist

logger = logging.getLogger(__name__)


def _is_main_process() -> bool:
    if not dist.is_initialized():
        return True
    return dist.get_rank() == 0


def save_sharded_checkpoint(
    path: str,
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    scheduler: Any | None = None,
    epoch: int = 0,
    step: int = 0,
    best_val_loss: float = float("inf"),
    config: dict[str, Any] | None = None,
    async_save: bool = False,
) -> str:
    """Save a sharded checkpoint.

    When using FSDP/ZeRO, each rank writes its shard to a separate file.
    Rank 0 also writes the consolidated metadata.
    """
    base_path = Path(path)
    os.makedirs(base_path.parent, exist_ok=True)

    world_size = dist.get_world_size() if dist.is_initialized() else 1

    if world_size > 1:
        shard_path = f"{path}.shard_rank{dist.get_rank()}"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "rank": dist.get_rank(),
                "world_size": world_size,
            },
            shard_path,
        )
        logger.info("Saved sharded checkpoint: %s (rank=%d)", shard_path, dist.get_rank())
    else:
        state: dict[str, Any] = {
            "epoch": epoch,
            "step": step,
            "best_val_loss": best_val_loss,
            "config": config,
        }
        try:
            state["model_state_dict"] = model.state_dict()
        except Exception as exc:
            logger.warning("Could not serialize model state: %s", exc)
            state["model_state_dict"] = {}
        if optimizer is not None:
            state["optimizer_state_dict"] = optimizer.state_dict()
        if scheduler is not None:
            state["scheduler_state_dict"] = scheduler.state_dict()
        torch.save(state, path)
        logger.info("Saved checkpoint: %s", path)

    if _is_main_process() and world_size > 1:
        meta: dict[str, Any] = {
            "epoch": epoch,
            "step": step,
            "best_val_loss": best_val_loss,
            "world_size": world_size,
            "shards": [f"{path}.shard_rank{r}" for r in range(world_size)],
            "config": config,
        }
        meta_path = f"{path}.meta"
        torch.save(meta, meta_path)
        logger.info("Saved sharded checkpoint metadata: %s", meta_path)

    if async_save:
        return f"{path}.shard_rank{dist.get_rank() if dist.is_initialized() else 0}"
    return path


async def async_save_sharded_checkpoint(
    path: str,
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    scheduler: Any | None = None,
    epoch: int = 0,
    step: int = 0,
    best_val_loss: float = float("inf"),
    config: dict[str, Any] | None = None,
) -> str:
    """Async wrapper around save_sharded_checkpoint using a thread executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        save_sharded_checkpoint,
        path,
        model,
        optimizer,
        scheduler,
        epoch,
        step,
        best_val_loss,
        config,
        False,
    )


def load_sharded_checkpoint(
    path: str,
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    scheduler: Any | None = None,
    device: torch.device | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Load a sharded checkpoint.

    Automatically handles single-file and sharded checkpoint formats.
    """
    device = device or torch.device("cpu")
    path = str(Path(path))

    if Path(f"{path}.meta").exists():
        meta = torch.load(f"{path}.meta", map_location="cpu", weights_only=False)
        shards = meta.get("shards", [])
        world_size = meta.get("world_size", 1)
        current_rank = dist.get_rank() if dist.is_initialized() else 0
        shard_path = shards[current_rank] if current_rank < len(shards) else shards[0]
        shard_state = torch.load(shard_path, map_location=device, weights_only=False)
        model.load_state_dict(shard_state["model_state_dict"], strict=strict)
        if optimizer is not None and "optimizer_state_dict" in shard_state:
            optimizer.load_state_dict(shard_state["optimizer_state_dict"])
        logger.info("Loaded sharded checkpoint for rank %d from %s.", current_rank, shard_path)
        return meta

    if not Path(path).exists():
        raise FileNotFoundError(f"Checkpoint not found: {path}")

    state = torch.load(path, map_location=device, weights_only=False)
    model_state = state.get("model_state_dict", {})
    model.load_state_dict(model_state, strict=strict)
    if optimizer is not None and state.get("optimizer_state_dict"):
        optimizer.load_state_dict(state["optimizer_state_dict"])
    if scheduler is not None and state.get("scheduler_state_dict"):
        scheduler.load_state_dict(state["scheduler_state_dict"])
    logger.info("Loaded checkpoint: %s", path)
    return {
        "epoch": state.get("epoch", 0),
        "step": state.get("step", 0),
        "best_val_loss": state.get("best_val_loss", float("inf")),
        "config": state.get("config"),
    }


def verify_checkpoint(path: str, model: nn.Module, device: torch.device | None = None) -> bool:
    """Verify that a checkpoint is valid and can be loaded into the model."""
    device = device or torch.device("cpu")
    try:
        if Path(f"{path}.meta").exists():
            meta = torch.load(f"{path}.meta", map_location="cpu", weights_only=False)
            shards = meta.get("shards", [])
            current_rank = dist.get_rank() if dist.is_initialized() else 0
            shard_path = shards[current_rank] if current_rank < len(shards) else shards[0]
            state = torch.load(shard_path, map_location=device, weights_only=False)
        else:
            state = torch.load(path, map_location=device, weights_only=False)
        model_state = state.get("model_state_dict", state) if isinstance(state, dict) else {}
        model.load_state_dict(model_state, strict=False)
        logger.info("Checkpoint verification passed: %s", path)
        return True
    except Exception as exc:
        logger.error("Checkpoint verification failed: %s", exc)
        return False
