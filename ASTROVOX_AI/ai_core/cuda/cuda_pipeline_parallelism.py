from typing import Optional, List
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.cuda.cuda_streams import CUDAStreamManager
from ASTROVOX_AI.ai_core.cuda.cuda_graphs import CUDAGraphManager


class CUDAPipelineParallelism:
    def __init__(self, stages: List[nn.Module], num_microbatches: int = 4, device_ids: Optional[List[int]] = None):
        self.stages = nn.ModuleList(stages)
        self.num_microbatches = num_microbatches
        self.device_ids = device_ids or list(range(len(stages)))
        self.stream_manager = CUDAStreamManager(num_streams=len(stages))
        self.graph_manager = CUDAGraphManager()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
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

    def schedule_1f1b(self, x: torch.Tensor) -> List[torch.Tensor]:
        microbatch_size = x.shape[0] // self.num_microbatches
        stage_outputs = [None] * self.num_microbatches
        for i in range(self.num_microbatches):
            micro = x[i * microbatch_size:(i + 1) * microbatch_size]
            for j, stage in enumerate(self.stages):
                micro = stage(micro)
            stage_outputs[i] = micro
        return stage_outputs
