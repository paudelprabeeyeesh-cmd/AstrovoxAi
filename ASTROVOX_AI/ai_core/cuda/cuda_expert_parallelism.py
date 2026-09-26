from typing import Optional, List, Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
import math

try:
    import triton
    import triton.language as tl
    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False


if TRITON_AVAILABLE:
    @triton.jit
    def _moe_dispatch_kernel(
        tokens_ptr, expert_indices_ptr, expert_probs_ptr,
        output_ptr, num_tokens, num_experts, top_k,
        stride_tok, stride_exp, stride_prob,
        stride_out, hidden_size,
        BLOCK_SIZE: tl.constexpr,
    ):
        pid = tl.program_id(0)
        start = pid * BLOCK_SIZE
        offsets = start + tl.arange(0, BLOCK_SIZE)
        mask = offsets < num_tokens
        token_idx = offsets
        for k in range(top_k):
            expert_id = tl.load(expert_indices_ptr + token_idx * stride_tok + k * stride_exp, mask=mask, other=0)
            prob = tl.load(expert_probs_ptr + token_idx * stride_tok + k * stride_prob, mask=mask, other=0.0)
            tl.atomic_add(output_ptr + expert_id * stride_out + token_idx * stride_tok, prob)


class Expert(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, activation: str = "gelu"):
        super().__init__()
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size
        self.activation = activation
        self.w1 = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.w2 = nn.Linear(intermediate_size, hidden_size, bias=False)
        self.w3 = nn.Linear(hidden_size, intermediate_size, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.activation == "gelu":
            return self.w2(F.gelu(self.w1(x)) * self.w3(x))
        elif self.activation == "silu":
            return self.w2(F.silu(self.w1(x)) * self.w3(x))
        else:
            return self.w2(self.w1(x))


class CUDAExpertParallelism:
    def __init__(self, num_experts: int, tp_size: int = 2, device_ids: Optional[List[int]] = None):
        self.num_experts = num_experts
        self.tp_size = tp_size
        self.device_ids = device_ids or list(range(tp_size))
        self.expert_devices: Dict[int, int] = {i: i % tp_size for i in range(num_experts)}
        self.experts = nn.ModuleList([None] * num_experts)
        self._initialize_experts()

    def _initialize_experts(self):
        for i in range(self.num_experts):
            device_id = self.expert_devices[i]
            self.experts[i] = Expert(768, 3072)
            self.experts[i] = self.experts[i].to(f'cuda:{device_id}')

    def dispatch(self, tokens: torch.Tensor, expert_indices: torch.Tensor, expert_probs: torch.Tensor) -> Dict[int, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
        dispatched: Dict[int, List[Tuple[torch.Tensor, torch.Tensor, int]]] = {i: [] for i in range(self.tp_size)}
        batch_size = tokens.shape[0]
        top_k = expert_indices.shape[-1]
        for b in range(batch_size):
            for k in range(top_k):
                expert_id = expert_indices[b, k].item()
                device_id = self.expert_devices[expert_id]
                dispatched[device_id].append((tokens[b], expert_probs[b, k], expert_id))
        return {d: (torch.stack([x[0] for x in items]), torch.stack([x[1] for x in items]), [x[2] for x in items]) for d, items in dispatched.items() if items}

    def combine(self, results: Dict[int, Tuple[torch.Tensor, torch.Tensor, List[int]]], output_shape: Tuple[int, int]) -> torch.Tensor:
        output = torch.zeros(output_shape, device=f'cuda:{self.device_ids[0]}', dtype=torch.float32)
        for device_id, (tokens, probs, expert_ids) in results.items():
            tokens = tokens.to(output.device)
            probs = probs.to(output.device)
            for i in range(tokens.shape[0]):
                output[i] += probs[i] * tokens[i]
        return output

    def forward(self, hidden_states: torch.Tensor, gate_logits: torch.Tensor, top_k: int = 2) -> torch.Tensor:
        B, T, C = hidden_states.shape
        top_k_weights, top_k_indices = torch.topk(gate_logits, top_k, dim=-1)
        top_k_weights = F.softmax(top_k_weights, dim=-1, dtype=torch.float32)
        hidden_states = hidden_states.view(-1, C)
        top_k_indices = top_k_indices.view(-1, top_k)
        top_k_weights = top_k_weights.view(-1, top_k)
        dispatched = self.dispatch(hidden_states, top_k_indices, top_k_weights)
        results = {}
        for device_id, (tokens, probs, expert_ids) in dispatched.items():
            expert_outputs = []
            for idx, expert_id in enumerate(expert_ids):
                expert_outputs.append(self.experts[expert_id](tokens[idx:idx + 1]))
            results[device_id] = (torch.cat(expert_outputs, dim=0), probs, expert_ids)
        combined = self.combine(results, (hidden_states.shape[0], C))
        return combined.view(B, T, C)


class CUDAExpertParallelismV2:
    def __init__(self, num_experts: int, tp_size: int, ep_size: int, hidden_size: int, intermediate_size: int, device_ids: Optional[List[int]] = None):
        self.num_experts = num_experts
        self.tp_size = tp_size
        self.ep_size = ep_size
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size
        self.device_ids = device_ids or list(range(ep_size))
        self.expert_devices: Dict[int, int] = {i: i % ep_size for i in range(num_experts)}
        self.experts = nn.ModuleList([Expert(hidden_size, intermediate_size) for _ in range(num_experts)])

    def dispatch(self, tokens: torch.Tensor, expert_indices: torch.Tensor, expert_probs: torch.Tensor) -> Dict[int, Tuple[torch.Tensor, torch.Tensor]]:
        dispatched: Dict[int, List[Tuple[torch.Tensor, torch.Tensor]]] = {i: [] for i in range(self.ep_size)}
        batch_size = tokens.shape[0]
        top_k = expert_indices.shape[-1]
        for b in range(batch_size):
            for k in range(top_k):
                expert_id = expert_indices[b, k].item()
                device_id = self.expert_devices[expert_id]
                dispatched[device_id].append((tokens[b], expert_probs[b, k]))
        return {d: (torch.stack([x[0] for x in items]), torch.stack([x[1] for x in items])) for d, items in dispatched.items() if items}

    def combine(self, results: Dict[int, Tuple[torch.Tensor, torch.Tensor]], output_shape: Tuple[int, int, int]) -> torch.Tensor:
        output = torch.zeros(output_shape, device=f'cuda:{self.device_ids[0]}', dtype=torch.float32)
        for device_id, (tokens, probs) in results.items():
            tokens = tokens.to(output.device)
            probs = probs.to(output.device)
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

    def forward(self, hidden_states: torch.Tensor, gate_logits: torch.Tensor, top_k: int = 2) -> torch.Tensor:
        B, T, C = hidden_states.shape
        top_k_weights, top_k_indices = torch.topk(gate_logits, top_k, dim=-1)
        top_k_weights = F.softmax(top_k_weights, dim=-1, dtype=torch.float32)
        hidden_states = hidden_states.view(-1, C)
        top_k_indices = top_k_indices.view(-1, top_k)
        top_k_weights = top_k_weights.view(-1, top_k)
        dispatched = self.dispatch(hidden_states, top_k_indices, top_k_weights)
        results = {}
        for device_id, (tokens, probs) in dispatched.items():
            expert_outputs = []
            expert_ids = list(set(top_k_indices.view(-1)[:len(tokens)].tolist()))
            for expert_id in expert_ids[:len(tokens)]:
                expert_outputs.append(self.experts[expert_id](tokens[len(expert_outputs):len(expert_outputs)+1]))
            results[device_id] = (torch.cat(expert_outputs, dim=0), probs)
        combined = self.combine(results, (hidden_states.shape[0], C))
        return combined.view(B, T, C)
