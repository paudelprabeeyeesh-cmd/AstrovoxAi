"""DeepSeek V2/R1 architecture reproduction with MLA and MoE."""

import logging
from typing import Any

import torch
import torch.nn as nn

from .base import ArchitectureSpec, BaseArchitecture

logger = logging.getLogger(__name__)


class DeepSeekRMSNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return x * norm * self.weight


class DeepSeekRotaryEmbedding(nn.Module):
    def __init__(self, dim: int, base: float = 10000.0):
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


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)


def apply_rotary_pos_emb(q: torch.Tensor, k: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    q = (q * cos) + (rotate_half(q) * sin)
    k = (k * cos) + (rotate_half(k) * sin)
    return q, k


class DeepSeekAttention(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        num_heads: int,
        num_kv_heads: int,
        head_dim: int,
        q_lora_rank: int,
        kv_lora_rank: int,
        rope_base: float = 10000.0,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = head_dim
        self.num_kv_groups = num_heads // num_kv_heads
        self.q_lora_rank = q_lora_rank
        self.kv_lora_rank = kv_lora_rank

        self.q_a_proj = nn.Linear(hidden_size, q_lora_rank, bias=False)
        self.q_a_norm = DeepSeekRMSNorm(q_lora_rank)
        self.q_b_proj = nn.Linear(q_lora_rank, num_heads * head_dim, bias=False)

        self.kv_a_proj = nn.Linear(hidden_size, kv_lora_rank + head_dim, bias=False)
        self.kv_a_norm = DeepSeekRMSNorm(kv_lora_rank)
        self.kv_b_proj = nn.Linear(kv_lora_rank, num_kv_heads * head_dim, bias=False)
        self.v_b_proj = nn.Linear(kv_lora_rank, num_kv_heads * head_dim, bias=False)

        self.o_proj = nn.Linear(num_heads * head_dim, hidden_size, bias=False)
        self.rope = DeepSeekRotaryEmbedding(head_dim, base=rope_base)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        B, T, C = x.size()

        q = self.q_b_proj(self.q_a_norm(self.q_a_proj(x)))
        q = q.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)

        kv = self.kv_a_proj(x)
        k = kv[..., : self.kv_lora_rank]
        v = kv[..., self.kv_lora_rank :]
        k = self.kv_a_norm(k)
        k = self.kv_b_proj(k).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_b_proj(v).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rope(T, x.device)
        q, k = apply_rotary_pos_emb(q, k, cos, sin)

        if self.num_kv_groups > 1:
            k = k.repeat_interleave(self.num_kv_groups, dim=1)
            v = v.repeat_interleave(self.num_kv_groups, dim=1)

        attn = torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=True)
        y = attn.transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(y)


class DeepSeekMoE(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        intermediate_size: int,
        num_experts: int,
        top_k: int,
    ):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = top_k
        self.gate = nn.Linear(hidden_size, num_experts, bias=False)
        self.shared_expert = nn.Sequential(
            nn.Linear(hidden_size, intermediate_size, bias=False),
            nn.SiLU(),
            nn.Linear(intermediate_size, hidden_size, bias=False),
        )
        self.shared_expert_gate = nn.Linear(hidden_size, 1, bias=False)
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_size, intermediate_size, bias=False),
                nn.SiLU(),
                nn.Linear(intermediate_size, hidden_size, bias=False),
            )
            for _ in range(num_experts)
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

        shared = self.shared_expert(x_flat)
        shared_gate = torch.sigmoid(self.shared_expert_gate(x_flat))
        out = out + shared_gate * shared
        return out.view(B, T, C)


class DeepSeekBlock(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        num_heads: int,
        num_kv_heads: int,
        intermediate_size: int,
        q_lora_rank: int,
        kv_lora_rank: int,
        rope_base: float,
        num_experts: int,
        top_k: int,
    ):
        super().__init__()
        self.norm1 = DeepSeekRMSNorm(hidden_size)
        self.attn = DeepSeekAttention(hidden_size, num_heads, num_kv_heads, hidden_size // num_heads, q_lora_rank, kv_lora_rank, rope_base)
        self.norm2 = DeepSeekRMSNorm(hidden_size)
        self.mlp = DeepSeekMoE(hidden_size, intermediate_size, num_experts, top_k)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), mask)
        x = x + self.mlp(self.norm2(x))
        return x


class DeepSeekModel(nn.Module):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config
        self.hidden_size = config["hidden_size"]
        self.vocab_size = config["vocab_size"]
        self.num_layers = config["num_layers"]
        self.num_heads = config["num_heads"]
        self.num_kv_heads = config.get("num_kv_heads", config["num_heads"])
        self.intermediate_size = config["intermediate_size"]
        self.q_lora_rank = config.get("q_lora_rank", 1536)
        self.kv_lora_rank = config.get("kv_lora_rank", 512)
        self.rope_base = config.get("rope_base", 10000.0)
        self.num_experts = config.get("num_experts", 64)
        self.top_k = config.get("top_k", 6)
        self.tie_weights = config.get("tie_weights", True)

        self.embed_tokens = nn.Embedding(self.vocab_size, self.hidden_size)
        self.layers = nn.ModuleList([
            DeepSeekBlock(
                self.hidden_size,
                self.num_heads,
                self.num_kv_heads,
                self.intermediate_size,
                self.q_lora_rank,
                self.kv_lora_rank,
                self.rope_base,
                self.num_experts,
                self.top_k,
            )
            for _ in range(self.num_layers)
        ])
        self.norm = DeepSeekRMSNorm(self.hidden_size)
        self.lm_head = nn.Linear(self.hidden_size, self.vocab_size, bias=False)
        if self.tie_weights:
            self.lm_head.weight = self.embed_tokens.weight

    def forward(self, input_ids: torch.Tensor, labels: torch.Tensor | None = None) -> dict[str, torch.Tensor]:
        x = self.embed_tokens(input_ids)
        for block in self.layers:
            x = block(x)
        x = self.norm(x)
        logits = self.lm_head(x)
        loss = None
        if labels is not None:
            loss = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1))
        return {"logits": logits, "loss": loss}


class DeepSeekArchitecture(BaseArchitecture):
    SPEC = ArchitectureSpec(
        name="deepseek",
        family="deepseek",
        paper="DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model",
        description="Decoder-only transformer with MLA, DeepSeekMoE, SwiGLU, and RMSNorm",
        config_path="models/llm/configs/config_deepseek.yaml",
        parameter_formula=" vocab*hidden + layers*(2*hidden + q_lora*hidden + q_lora*heads*head_dim + kv_lora*hidden + 2*kv_lora*kv_heads*head_dim + heads*head_dim*hidden + 3*hidden*ffn + hidden*num_experts + 3*hidden*ffn*num_experts) + hidden",
        key_innovations=["MLA", "DeepSeekMoE with shared expert", "SwiGLU", "no biases"],
        supported_features=["mla", "moe", "swiglu", "rms_norm", "weight_tying"],
    )

    def build(self, config: dict[str, Any]) -> nn.Module:
        return DeepSeekModel(config)

    def count_parameters(self, config: dict[str, Any]) -> int:
        vocab = config["vocab_size"]
        hidden = config["hidden_size"]
        layers = config["num_layers"]
        heads = config["num_heads"]
        kv_heads = config.get("num_kv_heads", heads)
        ffn = config["intermediate_size"]
        q_lora_rank = config.get("q_lora_rank", 1536)
        kv_lora_rank = config.get("kv_lora_rank", 512)
        num_experts = config.get("num_experts", 64)
        top_k = config.get("top_k", 6)
        head_dim = hidden // heads

        params = vocab * hidden

        per_block = 0
        per_block += 2 * hidden
        # MLA attention
        per_block += q_lora_rank * hidden + q_lora_rank * heads * head_dim
        per_block += kv_lora_rank * hidden + head_dim * hidden + 2 * kv_lora_rank * kv_heads * head_dim
        per_block += heads * head_dim * hidden
        # MoE: shared expert + gate + routed experts
        per_block += 3 * hidden * ffn + hidden * num_experts + top_k * num_experts * 3 * hidden * ffn

        params += layers * per_block
        params += hidden

        if not config.get("tie_weights", True):
            params += hidden * vocab

        return params

    def get_spec(self) -> ArchitectureSpec:
        return self.SPEC
