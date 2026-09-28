"""Distributed Data Parallel (DDP) wrapper for model training."""

from __future__ import annotations

import logging
from typing import Any

import torch
import torch.distributed as dist
import torch.nn as nn

logger = logging.getLogger(__name__)


class DDPWrapper:
    """Wraps a model with DistributedDataParallel.

    Handles gradient synchronization and multi-node setup via
    torch.distributed environment variables.
    """

    def __init__(
        self,
        model: nn.Module,
        device_ids: list[int] | None = None,
        output_device: int | None = None,
        find_unused_parameters: bool = False,
        gradient_as_bucket_view: bool = True,
        broadcast_buffers: bool = True,
    ) -> None:
        self._model = model
        self._device_ids = device_ids
        self._output_device = output_device
        self._find_unused_parameters = find_unused_parameters
        self._gradient_as_bucket_view = gradient_as_bucket_view
        self._broadcast_buffers = broadcast_buffers
        self._wrapped: nn.Module | None = None

    def init(self, device: torch.device) -> nn.Module:
        """Initialize DDP on the given device and return the wrapped model."""
        if not dist.is_available() or not dist.is_initialized():
            logger.warning("torch.distributed not initialized; returning raw model.")
            return self._model

        local_rank = int(dist.get_rank() % torch.cuda.device_count())
        device_ids = self._device_ids or [local_rank]
        output_device = self._output_device if self._output_device is not None else local_rank

        self._model = self._model.to(device)
        self._wrapped = nn.parallel.DistributedDataParallel(
            self._model,
            device_ids=device_ids,
            output_device=output_device,
            find_unused_parameters=self._find_unused_parameters,
            gradient_as_bucket_view=self._gradient_as_bucket_view,
            broadcast_buffers=self._broadcast_buffers,
        )
        logger.info(
            "DDP initialized: rank=%d, world_size=%d, device=%s",
            dist.get_rank(),
            dist.get_world_size(),
            device,
        )
        return self._wrapped

    @property
    def wrapped(self) -> nn.Module | None:
        return self._wrapped

    def unwrap(self) -> nn.Module:
        """Return the underlying model (through DDP if wrapped)."""
        return self._wrapped.module if self._wrapped is not None else self._model

    def state_dict(self) -> dict[str, Any]:
        target = self._wrapped if self._wrapped is not None else self._model
        return target.state_dict()

    def load_state_dict(self, state_dict: dict[str, Any], strict: bool = True) -> None:
        target = self._wrapped if self._wrapped is not None else self._model
        target.load_state_dict(state_dict, strict=strict)

    def parameters(self) -> Any:
        target = self._wrapped if self._wrapped is not None else self._model
        return target.parameters()

    def train(self, mode: bool = True) -> None:
        target = self._wrapped if self._wrapped is not None else self._model
        target.train(mode)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        target = self._wrapped if self._wrapped is not None else self._model
        return target(*args, **kwargs)


def synchronize_gradients(model: nn.Module) -> None:
    """Explicitly synchronize gradients across all ranks.

    Useful when using gradient accumulation without DDP's built-in sync.
    """
    if not dist.is_initialized():
        return
    for param in model.parameters():
        if param.grad is not None:
            dist.all_reduce(param.grad, op=dist.ReduceOp.SUM)
            param.grad.div_(dist.get_world_size())


def setup_multi_node(
    backend: str = "nccl",
    init_method: str | None = None,
) -> bool:
    """Initialize distributed process group for multi-node training.

    Reads RANK, WORLD_SIZE, LOCAL_RANK from environment.
    """
    if dist.is_initialized():
        return True
    if init_method is None:
        init_method = "env://"
    try:
        dist.init_process_group(backend=backend, init_method=init_method)
        logger.info(
            "Multi-node process group initialized: rank=%d, world_size=%d, backend=%s",
            dist.get_rank(),
            dist.get_world_size(),
            backend,
        )
        return True
    except Exception as exc:
        logger.error("Failed to initialize multi-node process group: %s", exc)
        return False
