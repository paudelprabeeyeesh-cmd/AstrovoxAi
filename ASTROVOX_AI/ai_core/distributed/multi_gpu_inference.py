from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.distributed.nccl import NCCLBackend


class MultiGPUInference:
    def __init__(self, model: nn.Module, device_ids: Optional[List[int]] = None, use_tensor_parallel: bool = True):
        self.device_ids = device_ids or list(range(torch.cuda.device_count()))
        self.num_gpus = len(self.device_ids)
        self.use_tensor_parallel = use_tensor_parallel
        self.backend = NCCLBackend(self.num_gpus, self.device_ids)
        if use_tensor_parallel and self.num_gpus > 1:
            from ASTROVOX_AI.ai_core.cuda.cuda_tensor_parallelism import CUDATensorParallelism
            self.tp = CUDATensorParallelism(model, self.num_gpus, self.device_ids)
            self.model = self.tp.shard_model()
        else:
            self.model = nn.DataParallel(model, device_ids=self.device_ids)

    def infer(self, input_ids: torch.Tensor, max_new_tokens: int = 100) -> torch.Tensor:
        self.model.eval()
        with torch.no_grad():
            output = self.model(input_ids)
        return output

    def tensor_parallel_generate(self, input_ids: torch.Tensor, max_new_tokens: int = 100) -> torch.Tensor:
        for _ in range(max_new_tokens):
            logits = self.tp.forward_step(input_ids)
            next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
            input_ids = torch.cat([input_ids, next_token], dim=1)
        return input_ids

    def cleanup(self) -> None:
        self.backend.cleanup()
