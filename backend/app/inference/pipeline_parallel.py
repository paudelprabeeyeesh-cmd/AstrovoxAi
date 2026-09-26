"""Pipeline parallelism service wrapper for distributed inference."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import torch
import torch.nn as nn

from ASTROVOX_AI.ai_core.inference.pipeline_parallelism import PipelineParallelism, PipelineConfig

logger = logging.getLogger(__name__)


class PipelineParallelService:
    def __init__(self, world_size: int = 1, rank: int = 0, num_stages: int = 1, micro_batch_size: int = 1):
        self.config = PipelineConfig(
            world_size=world_size,
            rank=rank,
            num_stages=num_stages,
            micro_batch_size=micro_batch_size,
        )
        self.pp = PipelineParallelism(self.config)

    def partition(self, model: nn.Module, num_stages: int) -> List[nn.Sequential]:
        return self.pp.partition(model, num_stages)

    def forward_stage(self, stage_idx: int, x: torch.Tensor) -> torch.Tensor:
        return self.pp.forward_stage(stage_idx, x)

    def schedule_1f1b(self, num_micro_batches: int) -> List[Tuple[int, str]]:
        return self.pp.schedule_1f1b(num_micro_batches)

    def initialize_buffers(self, shape: Tuple[int, int], device: torch.device, dtype: torch.dtype) -> None:
        self.pp.initialize_buffers(shape, device, dtype)

    def send(self, tensor: torch.Tensor, dest_rank: int) -> None:
        self.pp.send(tensor, dest_rank)

    def recv(self, src_rank: int) -> torch.Tensor:
        return self.pp.recv(src_rank)
