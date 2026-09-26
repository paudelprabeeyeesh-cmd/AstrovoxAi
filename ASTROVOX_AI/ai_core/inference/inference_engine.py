from typing import Optional, Tuple
import torch
import torch.nn as nn


class KVCache:
    def __init__(self, max_batch_size: int, max_seq_len: int, num_layers: int, num_heads: int, head_dim: int, device: torch.device):
        self.max_batch_size = max_batch_size
        self.max_seq_len = max_seq_len
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.device = device
        self.k_cache = [torch.zeros(max_batch_size, num_heads, max_seq_len, head_dim, device=device) for _ in range(num_layers)]
        self.v_cache = [torch.zeros(max_batch_size, num_heads, max_seq_len, head_dim, device=device) for _ in range(num_layers)]
        self.cache_len = [0] * num_layers

    def update(self, layer_idx: int, k: torch.Tensor, v: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        bsz = k.shape[0]
        seq_len = k.shape[2]
        self.k_cache[layer_idx][:bsz, :, self.cache_len[layer_idx]:self.cache_len[layer_idx] + seq_len, :] = k
        self.v_cache[layer_idx][:bsz, :, self.cache_len[layer_idx]:self.cache_len[layer_idx] + seq_len, :] = v
        k_out = self.k_cache[layer_idx][:bsz, :, :self.cache_len[layer_idx] + seq_len, :]
        v_out = self.v_cache[layer_idx][:bsz, :, :self.cache_len[layer_idx] + seq_len, :]
        self.cache_len[layer_idx] += seq_len
        return k_out, v_out

    def reset(self) -> None:
        for i in range(self.num_layers):
            self.k_cache[i].zero_()
            self.v_cache[i].zero_()
            self.cache_len[i] = 0


class InferenceEngine:
    def __init__(self, model: nn.Module, config, device: torch.device):
        self.model = model.to(device)
        self.config = config
        self.device = device
        self.cache: Optional[KVCache] = None

    def init_cache(self, batch_size: int = 1) -> None:
        self.cache = KVCache(
            max_batch_size=batch_size,
            max_seq_len=self.config.max_position_embeddings,
            num_layers=self.config.num_layers,
            num_heads=self.config.num_heads,
            head_dim=self.config.hidden_size // self.config.num_heads,
            device=self.device,
        )

    @torch.no_grad()
    def generate(self, input_ids: torch.Tensor, max_new_tokens: int = 100, temperature: float = 1.0, top_k: Optional[int] = None) -> torch.Tensor:
        self.init_cache(input_ids.shape[0])
        for _ in range(max_new_tokens):
            logits = self.model(input_ids)
            next_token_logits = logits[:, -1, :] / temperature
            if top_k is not None:
                v, _ = torch.topk(next_token_logits, top_k)
                next_token_logits[next_token_logits < v[:, [-1]]] = float('-inf')
            probs = F.softmax(next_token_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            input_ids = torch.cat([input_ids, next_token], dim=1)
        return input_ids
