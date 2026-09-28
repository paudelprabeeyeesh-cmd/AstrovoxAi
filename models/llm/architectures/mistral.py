"""Mistral and Mixtral architecture reproduction."""

import logging
from typing import Any, Dict

import torch
import torch.nn as nn

from .base import ArchitectureSpec, BaseArchitecture
from .llama import LlamaMLP, LlamaRMSNorm, apply_rotary_pos_emb

logger = logging.getLogger(__name__)


class MistralRotaryEmbedding(nn.Module):
    def __init__(self, dim: int, base: float = 1000000.0):
        super().__init__()
        self.dim = dim
        self.base = base
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)

    def forward(self, seq_len: int, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
        t = torch.arange(seq_len, device=device).type_as(self.inv_freq)
        freqs = torch.outer(t, self.inv_freq)
        emb = torch.cat((freqs, freqs), dim=-1)
        return emb.cos(), emb.sin()


class MistralAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, num_kv_heads: int, window_size: int | None = None, dropout: float = 0.0):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = hidden_size // num_heads
        self.window_size = window_size
        self.num_kv_groups = num_heads // num_kv_heads

        self.q_proj = nn.Linear(hidden_size, num_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(hidden_size, num_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(hidden_size, num_kv_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(num_heads * self.head_dim, hidden_size, bias=False)
        self.rope = MistralRotaryEmbedding(self.head_dim)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        B, T, C = x.size()
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rope(T, x.device)
        q, k = apply_rotary_pos_emb(q, k, cos, sin)

        if self.num_kv_groups > 1:
            k = k.repeat_interleave(self.num_kv_groups, dim=1)
            v = v.repeat_interleave(self.num_kv_groups, dim=1)

        if self.window_size is not None:
            mask = torch.triu(torch.ones(T, T, device=x.device), diagonal=self.window_size + 1).bool()

        attn = torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=True, attn_mask=mask)
        y = attn.transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(y)


class MixtralMoELayer(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, num_experts: int = 8, top_k: int = 2):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = top_k
        self.gate = nn.Linear(hidden_size, num_experts, bias=False)
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_size, intermediate_size, bias=False),
                nn.SiLU(),
                nn.Linear(intermediate_size, hidden_size, bias=False),
            ) for _ in range(num_experts)
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.size()
        x_flat = x.view(-1, C)
        gate_logits = self.gate(x_flat)
        topk_vals, topk_indices = torch.topk(gate_logits, self.top_k, dim=-1)
        topk_vals = torch.softmax(topk_vals, dim=-1)

        out = torch.zeros_like(x_flat)
        for i in range(self.top_k):
            expert_idx = topk_indices[:, i]
            expert_weight = topk_vals[:, i].unsqueeze(-1)
            for e in range(self.num_experts):
                mask = (expert_idx == e)
                if mask.any():
                    out[mask] += expert_weight[mask] * self.experts[e](x_flat[mask])
        return out.view(B, T, C)


class MistralBlock(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, num_kv_heads: int, intermediate_size: int, window_size: int | None = None, use_moe: bool = False, num_experts: int = 8, top_k: int = 2):
        super().__init__()
        self.norm1 = LlamaRMSNorm(hidden_size)
        self.attn = MistralAttention(hidden_size, num_heads, num_kv_heads, window_size)
        self.norm2 = LlamaRMSNorm(hidden_size)
        if use_moe:
            self.mlp = MixtralMoELayer(hidden_size, intermediate_size, num_experts, top_k)
        else:
            self.mlp = LlamaMLP(hidden_size, intermediate_size)
        self.rope = MistralRotaryEmbedding(hidden_size // num_heads)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        seq_len = x.size(1)
        cos, sin = self.rope(seq_len, x.device)
        x = x + self.attn(self.norm1(x), mask)
        x = x + self.mlp(self.norm2(x))
        return x


class MistralModel(nn.Module):
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.hidden_size = config["hidden_size"]
        self.vocab_size = config["vocab_size"]
        self.num_layers = config["num_layers"]
        self.num_heads = config["num_heads"]
        self.num_kv_heads = config.get("num_kv_heads", config["num_heads"])
        self.intermediate_size = config["intermediate_size"]
        self.window_size = config.get("window_size")
        self.use_moe = config.get("use_moe", False)
        self.num_experts = config.get("num_experts", 8)
        self.top_k = config.get("top_k", 2)
        self.tie_weights = config.get("tie_weights", True)

        self.embed_tokens = nn.Embedding(self.vocab_size, self.hidden_size)
        self.layers = nn.ModuleList([
            MistralBlock(self.hidden_size, self.num_heads, self.num_kv_heads, self.intermediate_size, self.window_size, self.use_moe, self.num_experts, self.top_k)
            for _ in range(self.num_layers)
        ])
        self.norm = LlamaRMSNorm(self.hidden_size)
        self.lm_head = nn.Linear(self.hidden_size, self.vocab_size, bias=False)
        if self.tie_weights:
            self.lm_head.weight = self.embed_tokens.weight

    def forward(self, input_ids: torch.Tensor, labels: torch.Tensor | None = None) -> Dict[str, torch.Tensor]:
        x = self.embed_tokens(input_ids)
        for block in self.layers:
            x = block(x)
        x = self.norm(x)
        logits = self.lm_head(x)
        loss = None
        if labels is not None:
            loss = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1))
        return {"logits": logits, "loss": loss}


class MistralArchitecture(BaseArchitecture):
    SPEC = ArchitectureSpec(
        name="mistral",
        family="mistral",
        paper="Mistral 7B and Mixtral 8x7B",
        description="LLaMA-derived architecture with sliding window attention and GQA",
        config_path="models/llm/configs/config_mistral.yaml",
        parameter_formula=" vocab*hidden + layers*(3*hidden + hidden*ffn + 4*hidden^2 + 2*hidden*ffn) + hidden",
        key_innovations=["sliding window attention", "GQA", "SiLU activation", "no biases"],
        supported_features=["rms_norm", "rope", "swiglu", "gqa", "sliding_window", "moe"],
    )

    def build(self, config: Dict[str, Any]) -> nn.Module:
        return MistralModel(config)

    def count_parameters(self, config: Dict[str, Any]) -> int:
        vocab = config["vocab_size"]
        hidden = config["hidden_size"]
        layers = config["num_layers"]
        heads = config["num_heads"]
        kv_heads = config.get("num_kv_heads", heads)
        ffn = config["intermediate_size"]
        use_moe = config.get("use_moe", False)
        num_experts = config.get("num_experts", 8)
        top_k = config.get("top_k", 2)

        params = vocab * hidden

        per_block = 0
        per_block += 2 * hidden  # 2 RMSNorm
        # Attention: Q + K + V + O (no bias)
        q_params = hidden * hidden
        k_params = kv_heads * (hidden // heads) * hidden
        v_params = kv_heads * (hidden // heads) * hidden
        o_params = hidden * hidden
        per_block += q_params + k_params + v_params + o_params
        # MLP
        if use_moe:
            gate_params = hidden * num_experts
            expert_params = top_k * num_experts * (2 * hidden * ffn)
            per_block += gate_params + expert_params
        else:
            per_block += 3 * hidden * ffn

        params += layers * per_block
        params += hidden

        if not config.get("tie_weights", True):
            params += hidden * vocab

        return params

    def get_spec(self) -> ArchitectureSpec:
        return self.SPEC
