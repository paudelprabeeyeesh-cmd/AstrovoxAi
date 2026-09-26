"""CUDA optimization service wrapper for inference workloads."""

from __future__ import annotations

import logging
from typing import Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class CUDAOptimizationService:
    def __init__(self, model: nn.Module, device: int = 0, use_fp16: bool = True, use_cuda_graphs: bool = True):
        self.device = device
        self.use_fp16 = use_fp16
        self.use_cuda_graphs = use_cuda_graphs
        self.model = model.to(f"cuda:{device}")
        if use_fp16:
            self.model.half()
        self._optimized = False
        from ASTROVOX_AI.ai_core.cuda.cuda_streams import CUDAStreamManager
        from ASTROVOX_AI.ai_core.cuda.cuda_graphs import CUDAGraphManager
        self.stream_manager = CUDAStreamManager(num_streams=4, device=device)
        self.graph_manager = CUDAGraphManager(device=device)

    def optimize(self) -> nn.Module:
        self.model.eval()
        self._optimized = True
        return self.model

    def capture_graph(self, dummy_input: torch.Tensor) -> None:
        if not self.use_cuda_graphs:
            return
        self.graph_manager.capture_full_model(self.model, dummy_input, "main")

    def replay(self) -> None:
        if not self.use_cuda_graphs:
            return
        self.graph_manager.replay("main")

    def warmup(self, dummy_input: torch.Tensor, steps: int = 10) -> None:
        with torch.no_grad():
            for _ in range(steps):
                if self.use_cuda_graphs:
                    self.replay()
                else:
                    self.model(dummy_input)
        torch.cuda.synchronize(self.device)

    def get_memory_stats(self) -> dict:
        if not torch.cuda.is_available():
            return {"error": "CUDA not available"}
        return {
            "allocated": torch.cuda.memory_allocated(self.device),
            "reserved": torch.cuda.memory_reserved(self.device),
            "max_allocated": torch.cuda.max_memory_allocated(self.device),
        }
