from typing import Optional, List, Dict, Any
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.cuda.cuda_tensor_parallelism import CUDATensorParallelism


class CUDAExpertParallelism:
    def __init__(self, num_experts: int, tp_size: int = 2, device_ids: Optional[List[int]] = None):
        self.num_experts = num_experts
        self.tp_size = tp_size
        self.device_ids = device_ids or list(range(tp_size))
        self.expert_devices: Dict[int, int] = {i: i % tp_size for i in range(num_experts)}
        self.tensor_parallel = CUDATensorParallelism(None, tp_size, device_ids)

    def dispatch(self, tokens: torch.Tensor, expert_indices: torch.Tensor, expert_probs: torch.Tensor) -> Dict[int, List[torch.Tensor]]:
        dispatched = {i: [] for i in range(self.tp_size)}
        for i in range(tokens.shape[0]):
            for j in range(expert_indices.shape[-1]):
                expert_id = expert_indices[i, j].item()
                device_id = self.expert_devices[expert_id]
                dispatched[device_id].append((tokens[i], expert_probs[i, j], expert_id))
        return dispatched

    def combine(self, results: Dict[int, List[torch.Tensor]], output_shape: tuple) -> torch.Tensor:
        output = torch.zeros(output_shape, device=f'cuda:{self.device_ids[0]}')
        for device_id, device_results in results.items():
            for token, prob, expert_id in device_results:
                output[token] += prob * device_results
        return output
