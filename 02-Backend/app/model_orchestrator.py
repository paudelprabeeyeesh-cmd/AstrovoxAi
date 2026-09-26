"""
Distributed model orchestration with pipeline and tensor parallelism.
"""

from __future__ import annotations

import logging
from typing import Optional, List
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class ModelOrchestrator:
    def __init__(self, model: nn.Module, world_size: int, rank: int, backend: str = "nccl"):
        self.model = model
        self.world_size = world_size
        self.rank = rank
        self.backend = backend
        self.pipeline_stages: Optional[List[nn.Module]] = None
        self.tensor_parallel_groups: Optional[List[int]] = None

    def setup_pipeline_parallelism(self, num_stages: int) -> List[nn.Module]:
        modules = list(self.model.children())
        stage_size = max(1, len(modules) // num_stages)
        stages = []
        for i in range(0, len(modules), stage_size):
            stage = nn.Sequential(*modules[i:i + stage_size])
            stages.append(stage)
        self.pipeline_stages = stages
        logger.info("Setup pipeline parallelism with %d stages on rank %d", len(stages), self.rank)
        return stages

    def setup_tensor_parallelism(self, tp_size: int) -> nn.Module:
        from ASTROVOX_AI.ai_core.cuda.cuda_tensor_parallelism import CUDATensorParallelism
        tp = CUDATensorParallelism(self.model, tp_size)
        self.tensor_parallel_groups = list(range(tp_size))
        return tp

    def forward(self, x: torch.Tensor, use_pipeline: bool = False) -> torch.Tensor:
        if use_pipeline and self.pipeline_stages is not None:
            output = x
            for stage in self.pipeline_stages:
                device = next(stage.parameters()).device
                output = stage(output.to(device))
            return output
        return self.model(x)

    def save_sharded_checkpoint(self, path: str) -> None:
        if self.pipeline_stages is None:
            torch.save(self.model.state_dict(), path)
        else:
            for i, stage in enumerate(self.pipeline_stages):
                torch.save(stage.state_dict(), f"{path}_stage_{i}.pt")

    def load_sharded_checkpoint(self, path: str) -> None:
        if self.pipeline_stages is None:
            self.model.load_state_dict(torch.load(path, map_location="cpu"))
        else:
            for i, stage in enumerate(self.pipeline_stages):
                stage.load_state_dict(torch.load(f"{path}_stage_{i}.pt", map_location="cpu"))
