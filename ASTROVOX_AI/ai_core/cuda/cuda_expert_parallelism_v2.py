from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class ExpertParallelismWithAlltoAll:
    def __init__(self, num_experts: int, tp_size: int, ep_size: int, hidden_size: int, intermediate_size: int, device_ids: Optional[List[int]] = None):
        self.num_experts = num_experts
        self.tp_size = tp_size
        self.ep_size = ep_size
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size
        self.device_ids = device_ids or list(range(ep_size))
        self.expert_devices: Dict[int, int] = {i: i % ep_size for i in range(num_experts)}
        self.experts = nn.ModuleList([nn.Sequential(nn.Linear(hidden_size, intermediate_size), nn.GELU(), nn.Linear(intermediate_size, hidden_size)) for _ in range(num_experts)])

    def dispatch(self, tokens: torch.Tensor, expert_indices: torch.Tensor, expert_probs: torch.Tensor) -> Dict[int, Tuple[torch.Tensor, torch.Tensor]]:
        dispatched: Dict[int, List[Tuple[torch.Tensor, torch.Tensor]]] = {i: [] for i in range(self.ep_size)}
        batch_size = tokens.shape[0]
        for b in range(batch_size):
            for k in range(expert_indices.shape[-1]):
                expert_id = expert_indices[b, k].item()
                device_id = self.expert_devices[expert_id]
                dispatched[device_id].append((tokens[b], expert_probs[b, k]))
        return {d: (torch.stack([x[0] for x in items]), torch.stack([x[1] for x in items])) for d, items in dispatched.items() if items}

    def combine(self, results: Dict[int, Tuple[torch.Tensor, torch.Tensor]], output_shape: Tuple[int, int, int]) -> torch.Tensor:
        output = torch.zeros(output_shape, device=f'cuda:{self.device_ids[0]}')
        for device_id, (tokens, probs) in results.items():
            for i in range(tokens.shape[0]):
                output[i] += probs[i] * tokens[i]
        return output

    def alltoall(self, tokens: torch.Tensor, expert_indices: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size = tokens.shape[0]
        recv_counts = torch.zeros(self.ep_size, dtype=torch.long, device=tokens.device)
        for b in range(batch_size):
            for k in range(expert_indices.shape[-1]):
                expert_id = expert_indices[b, k].item()
                recv_counts[self.expert_devices[expert_id]] += 1
        send_buffers: Dict[int, torch.Tensor] = {}
        recv_buffers: Dict[int, torch.Tensor] = {}
        for d in range(self.ep_size):
            if recv_counts[d] > 0:
                recv_buffers[d] = torch.zeros(recv_counts[d].item(), *tokens.shape[1:], device=f'cuda:{self.device_ids[d]}')
        return tokens, torch.zeros(batch_size, device=tokens.device)
