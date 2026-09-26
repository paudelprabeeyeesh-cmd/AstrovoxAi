from typing import Optional, List, Dict
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.cuda.cuda_streams import CUDAStreamManager
from ASTROVOX_AI.ai_core.cuda.cuda_graphs import CUDAGraphManager
from ASTROVOX_AI.ai_core.cuda.cuda_fusion import CUDAFusedOp


class EnhancedPipelineParallelism:
    def __init__(self, stages: List[nn.Module], num_microbatches: int = 4, device_ids: Optional[List[int]] = None, use_cuda_graphs: bool = True):
        self.stages = nn.ModuleList(stages)
        self.num_microbatches = num_microbatches
        self.device_ids = device_ids or list(range(len(stages)))
        self.stream_manager = CUDAStreamManager(num_streams=len(stages))
        self.graph_manager = CUDAGraphManager() if use_cuda_graphs else None
        self.stage_outputs: List[torch.Tensor] = []

    def forward_1f1b(self, x: torch.Tensor) -> torch.Tensor:
        microbatch_size = x.shape[0] // self.num_microbatches
        stage_outputs: Dict[int, List[torch.Tensor]] = {i: [] for i in range(self.num_microbatches)}
        for t in range(self.num_microbatches):
            micro = x[t * microbatch_size:(t + 1) * microbatch_size]
            for stage_idx, stage in enumerate(self.stages):
                device = torch.device(f'cuda:{self.device_ids[stage_idx]}')
                micro = micro.to(device)
                stream = self.stream_manager.get_stream()
                with torch.cuda.stream(stream):
                    micro = CUDAFusedOp.fused_dropout_residual_add(micro, micro, dropout=0.0, training=False)
                    micro = stage(micro)
                stage_outputs[t].append(micro)
        final_outputs = [stage_outputs[t][-1] for t in range(self.num_microbatches)]
        return torch.cat(final_outputs, dim=0)

    def forward_interleaved(self, x: torch.Tensor, chunks: int = 2) -> torch.Tensor:
        microbatch_size = x.shape[0] // self.num_microbatches
        outputs = []
        for i in range(self.num_microbatches):
            micro = x[i * microbatch_size:(i + 1) * microbatch_size]
            for j, stage in enumerate(self.stages):
                device = torch.device(f'cuda:{self.device_ids[j]}')
                micro = micro.to(device)
                stream = self.stream_manager.get_stream()
                with torch.cuda.stream(stream):
                    micro = stage(micro)
            outputs.append(micro)
        return torch.cat(outputs, dim=0)

    def schedule_zero_bubble(self, x: torch.Tensor) -> List[torch.Tensor]:
        microbatch_size = x.shape[0] // self.num_microbatches
        stage_outputs = [None] * self.num_microbatches
        num_stages = len(self.stages)
        for t in range(self.num_microbatches):
            micro = x[t * microbatch_size:(t + 1) * microbatch_size]
            for s in range(num_stages):
                device = torch.device(f'cuda:{self.device_ids[s]}')
                micro = micro.to(device)
                stream = self.stream_manager.get_stream()
                with torch.cuda.stream(stream):
                    micro = self.stages[s](micro)
            stage_outputs[t] = micro
        return stage_outputs
