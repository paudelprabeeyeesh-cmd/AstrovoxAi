"""Fully Sharded Data Parallel (FSDP) wrapper with gradient checkpointing integration."""

from __future__ import annotations

import logging
from typing import Any

import torch
import torch.distributed as dist
import torch.nn as nn

logger = logging.getLogger(__name__)


def _default_mp():
    try:
        from torch.distributed.fsdp import MixedPrecision

        return MixedPrecision(
            param_dtype=torch.float16,
            reduce_dtype=torch.float16,
            buffer_dtype=torch.float32,
        )
    except ImportError:
        return None


def _default_backward_prefetch():
    try:
        from torch.distributed.fsdp import BackwardPrefetch

        return BackwardPrefetch.BACKWARD_PRE
    except ImportError:
        return None


class FSDPWrapper:
    """FSDP wrapper that shards optimizer states, gradients, and parameters.

    Integrates with gradient checkpointing to reduce peak memory usage
    during the forward pass.
    """

    def __init__(
        self,
        model: nn.Module,
        cpu_offload: bool = False,
        mixed_precision: Any | None = None,
        sharding_strategy: Any | None = None,
        auto_wrap_policy: Any | None = None,
        use_gradient_checkpointing: bool = False,
        forward_prefetch: bool = True,
        backward_prefetch: Any | None = None,
        limit_all_gathers: bool = True,
    ) -> None:
        self._model = model
        self._cpu_offload = cpu_offload
        self._mixed_precision = mixed_precision
        self._use_gc = use_gradient_checkpointing
        self._wrapped: nn.Module | None = None
        self._sharding_strategy = sharding_strategy
        self._auto_wrap_policy = auto_wrap_policy
        self._forward_prefetch = forward_prefetch
        self._backward_prefetch = backward_prefetch
        self._limit_all_gathers = limit_all_gathers

    def init(self, device: torch.device) -> nn.Module:
        """Initialize FSDP and return the wrapped model."""
        if not dist.is_available() or not dist.is_initialized():
            logger.warning("torch.distributed not initialized; returning raw model.")
            return self._model

        try:
            from torch.distributed.fsdp import (
                FullyShardedDataParallel as FSDP,
                ShardingStrategy,
            )
        except ImportError:
            logger.error("FSDP is not available in this PyTorch build.")
            return self._model

        mp = self._mixed_precision or _default_mp()
        strategy = self._sharding_strategy or ShardingStrategy.FULL_SHARD
        bp = self._backward_prefetch or _default_backward_prefetch()

        self._model = self._model.to(device)

        if self._use_gc:
            self._model = self._apply_gradient_checkpointing(self._model)

        self._wrapped = FSDP(
            self._model,
            cpu_offload=self._cpu_offload,
            mixed_precision=mp,
            auto_wrap_policy=self._auto_wrap_policy,
            sharding_strategy=strategy,
            backward_prefetch=bp,
            forward_prefetch=self._forward_prefetch,
            limit_all_gathers=self._limit_all_gathers,
        )
        logger.info(
            "FSDP initialized: rank=%d, strategy=%s, cpu_offload=%s, gc=%s",
            dist.get_rank(),
            strategy,
            self._cpu_offload,
            self._use_gc,
        )
        return self._wrapped

    def _apply_gradient_checkpointing(self, module: nn.Module) -> nn.Module:
        """Apply gradient checkpointing to reduce peak memory usage."""
        try:
            from torch.utils.checkpoint import checkpoint

            for name, child in module.named_modules():
                if isinstance(child, (nn.TransformerEncoderLayer, nn.TransformerDecoderLayer)):
                    original_forward = child.forward

                    def _checkpointed_forward(*args: Any, **kwargs: Any):
                        return checkpoint(original_forward, *args, use_reentrant=False, **kwargs)

                    child.forward = _checkpointed_forward
        except ImportError:
            logger.warning("torch.utils.checkpoint unavailable; skipping gradient checkpointing.")
        return module

    @property
    def wrapped(self) -> nn.Module | None:
        return self._wrapped

    def unwrap(self) -> nn.Module:
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
