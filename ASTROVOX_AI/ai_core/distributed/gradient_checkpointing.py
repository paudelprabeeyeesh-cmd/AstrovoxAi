"""Gradient checkpointing: selective activation recomputation."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional, Tuple

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class GradientCheckpointingWrapper(nn.Module):
    def __init__(self, module: nn.Module, use_reentrant: bool = False):
        super().__init__()
        self.module = module
        self.use_reentrant = use_reentrant

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        return torch.utils.checkpoint.checkpoint(
            self.module, *args, use_reentrant=self.use_reentrant, **kwargs
        )


class GradientCheckpointManager:
    def __init__(self, enabled: bool = True, num_segments: int = 4):
        self.enabled = enabled
        self.num_segments = num_segments
        self._checkpointed_modules: List[nn.Module] = []

    def apply_checkpointing(self, module: nn.Module) -> None:
        if not self.enabled:
            return
        children = list(module.children())
        if not children:
            return
        segment_size = max(1, len(children) // self.num_segments)
        segments: List[nn.Module] = []
        for i in range(0, len(children), segment_size):
            segment = nn.Sequential(*children[i:i + segment_size])
            segments.append(GradientCheckpointingWrapper(segment))
        for idx, segment in enumerate(segments):
            setattr(module, f"_checkpointed_segment_{idx}", segment)
            self._checkpointed_modules.append(segment)
        logger.info("Applied gradient checkpointing across %d segments", len(segments))

    def checkpoint_forward(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        if self.enabled:
            return torch.utils.checkpoint.checkpoint(fn, *args, use_reentrant=False, **kwargs)
        return fn(*args, **kwargs)

    def get_memory_savings_estimate(self, total_params: int, num_layers: int) -> Dict[str, int]:
        original_activations = total_params * 4
        checkpointed_activations = original_activations // self.num_segments
        return {
            "original_activations_bytes": original_activations,
            "checkpointed_activations_bytes": checkpointed_activations,
            "saved_bytes": original_activations - checkpointed_activations,
            "recomputed_bytes": checkpointed_activations,
        }
