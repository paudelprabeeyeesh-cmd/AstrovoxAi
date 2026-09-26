"""
Model merging utilities for checkpoint merging and SLERP interpolation.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import torch.nn as nn

from ASTROVOX_AI.ai_core.training.checkpoint_merging import CheckpointMerger

logger = logging.getLogger(__name__)


class ModelMerger:
    @staticmethod
    def merge(models: List[nn.Module], weights: Optional[List[float]] = None) -> nn.Module:
        return CheckpointMerger.merge_models(models, weights=weights, method="linear")

    @staticmethod
    def slerp(model_a: nn.Module, model_b: nn.Module, t: float = 0.5) -> nn.Module:
        return CheckpointMerger.slerp(model_a, model_b, t=t)
