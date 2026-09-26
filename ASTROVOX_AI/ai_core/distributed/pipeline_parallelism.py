"""Pipeline parallelism: stage-based partitioning, 1F1B scheduling."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import torch
import torch.nn as nn
import torch.distributed as dist

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    world_size: int = 1
    rank: int = 0
    num_stages: int = 1
    micro_batch_size: int = 1
    stage_idx: int = 0


class PipelineParallelism:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank
        self.num_stages = config.num_stages
        self.micro_batch_size = config.micro_batch_size
        self.stage_idx = config.stage_idx
        self.stages: List[nn.Module] = []
        self._send_buffer: Optional[torch.Tensor] = None
        self._recv_buffer: Optional[torch.Tensor] = None

    def partition(self, model: nn.Module, num_stages: int) -> List[nn.Module]:
        modules = list(model.children())
        if not modules:
            modules = [model]
        stage_size = max(1, len(modules) // num_stages)
        stages = []
        for i in range(0, len(modules), stage_size):
            stage = nn.Sequential(*modules[i:i + stage_size])
            stages.append(stage)
        self.stages = stages
        logger.info("Partitioned model into %d pipeline stages", len(stages))
        return stages

    def forward_stage(self, stage_idx: int, x: torch.Tensor) -> torch.Tensor:
        if stage_idx >= len(self.stages):
            raise ValueError(f"Stage {stage_idx} does not exist")
        stage = self.stages[stage_idx]
        device = next(stage.parameters()).device
        return stage(x.to(device))

    def backward_stage(self, stage_idx: int, grad_output: torch.Tensor) -> torch.Tensor:
        if stage_idx >= len(self.stages):
            raise ValueError(f"Stage {stage_idx} does not exist")
        stage = self.stages[stage_idx]
        for param in stage.parameters():
            if param.grad is not None:
                param.grad = param.grad + grad_output.to(param.device)
        return grad_output

    def schedule_1f1b(self, num_micro_batches: int) -> List[Tuple[int, str]]:
        schedule: List[Tuple[int, str]] = []
        for mb in range(num_micro_batches):
            if self.rank < self.num_stages - 1:
                schedule.append((mb, "forward"))
            if self.rank > 0:
                schedule.append((mb, "backward"))
        return schedule

    def initialize_buffers(self, shape: Tuple[int, ...], device: torch.device, dtype: torch.dtype) -> None:
        self._send_buffer = torch.empty(shape, device=device, dtype=dtype)
        self._recv_buffer = torch.empty(shape, device=device, dtype=dtype)

    def send(self, tensor: torch.Tensor, dest_rank: int) -> None:
        if self._send_buffer is None:
            self._send_buffer = tensor.clone()
        else:
            self._send_buffer.copy_(tensor)
        dist.send(self._send_buffer, dst=dest_rank)

    def recv(self, src_rank: int) -> torch.Tensor:
        if self._recv_buffer is None:
            self._recv_buffer = torch.empty_like(self._send_buffer)
        dist.recv(self._recv_buffer, src=src_rank)
        return self._recv_buffer.clone()

    def run_1f1b(self, micro_batches: List[torch.Tensor], stages: Optional[List[nn.Module]] = None) -> List[torch.Tensor]:
        stages = stages or self.stages
        num_micro = len(micro_batches)
        outputs: List[torch.Tensor] = []
        for mb_idx in range(num_micro):
            x = micro_batches[mb_idx]
            for stage in stages:
                device = next(stage.parameters()).device
                x = stage(x.to(device))
            outputs.append(x)
        return outputs
