"""LLaMA 2/3 architecture reproduction."""

import logging
from typing import Any, Dict

import torch
import torch.nn as nn

from .base import ArchitectureSpec, BaseArchitecture

logger = logging.getLogger(__name__)


class LlamaRMSNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return x * norm * self.weight


class LlamaRotaryEmbedding(nn.Module):
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


class LlamaAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, num_kv_heads: int | None = None, dropout: float = 0.0):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads or num_heads
        self.head_dim = hidden_size // num_heads
        self.num_kv_groups = num_heads // self.num_kv_heads

        self.q_proj = nn.Linear(hidden_size, num_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(hidden_size, self.num_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(hidden_size, self.num_kv_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(num_heads * self.head_dim, hidden_size, bias=False)
        self.dropout = dropout

    def forward(self, x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        B, T, C = x.size()
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)

        q, k = apply_rotary_pos_emb(q, k, cos[:T], sin[:T])

        if self.num_kv_groups > 1:
            k = k.repeat_interleave(self.num_kv_groups, dim=1)
            v = v.repeat_interleave(self.num_kv_groups, dim=1)

        attn = torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=True)
        y = attn.transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(y)


class LlamaMLP(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int):
        super().__init__()
        self.gate_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.up_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.down_proj = nn.Linear(intermediate_size, hidden_size, bias=False)
        self.activation = nn.SiLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(self.activation(self.gate_proj(x)) * self.up_proj(x))


class LlamaBlock(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, num_kv_heads: int | None, intermediate_size: int, rope_base: float = 500000.0):
        super().__init__()
        self.norm1 = LlamaRMSNorm(hidden_size)
        self.attn = LlamaAttention(hidden_size, num_heads, num_kv_heads)
        self.norm2 = LlamaRMSNorm(hidden_size)
        self.mlp = LlamaMLP(hidden_size, intermediate_size)
        self.rope = LlamaRotaryEmbedding(hidden_size // num_heads, base=rope_base)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        seq_len = x.size(1)
        cos, sin = self.rope(seq_len, x.device)
        x = x + self.attn(self.norm1(x), cos, sin, mask)
        x = x + self.mlp(self.norm2(x))
        return x


class LlamaModel(nn.Module):
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.hidden_size = config["hidden_size"]
        self.vocab_size = config["vocab_size"]
        self.num_layers = config["num_layers"]
        self.num_heads = config["num_heads"]
        self.num_kv_heads = config.get("num_kv_heads")
        self.intermediate_size = config["intermediate_size"]
        self.rope_base = config.get("rope_base", 500000.0)
        self.tie_weights = config.get("tie_weights", True)

        self.embed_tokens = nn.Embedding(self.vocab_size, self.hidden_size)
        self.layers = nn.ModuleList([
            LlamaBlock(self.hidden_size, self.num_heads, self.num_kv_heads, self.intermediate_size, self.rope_base)
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


class LlamaArchitecture(BaseArchitecture):
    SPEC = ArchitectureSpec(
        name="llama",
        family="llama",
        paper="LLaMA: Open and Efficient Foundation Language Models",
        description="Decoder-only transformer with RMSNorm, RoPE, SwiGLU, and GQA support",
        config_path="models/llm/configs/config_llama.yaml",
        parameter_formula=" vocab*hidden + layers*(3*hidden + hidden*ffn + 4*hidden^2 + 2*hidden*ffn) + hidden",
        key_innovations=["RMSNorm", "SwiGLU", "RoPE", "GQA", "no biases"],
        supported_features=["rms_norm", "rope", "swiglu", "gqa", "weight_tying"],
    )

    def build(self, config: Dict[str, Any]) -> nn.Module:
        return LlamaModel(config)

    def count_parameters(self, config: Dict[str, Any]) -> int:
        vocab = config["vocab_size"]
        hidden = config["hidden_size"]
        layers = config["num_layers"]
        heads = config["num_heads"]
        kv_heads = config.get("num_kv_heads", heads)
        ffn = config["intermediate_size"]

        params = vocab * hidden  # token embeddings

        per_block = 0
        # RMSNorm: 1 * hidden (gamma only)
        per_block += 2 * hidden
        # Attention: Q + K + V + O projections (no bias)
        q_params = hidden * hidden
        k_params = kv_heads * (hidden // heads) * hidden
        v_params = kv_heads * (hidden // heads) * hidden
        o_params = hidden * hidden
        per_block += q_params + k_params + v_params + o_params
        # MLP: gate + up + down (SwiGLU, no bias)
        per_block += 3 * hidden * ffn

        params += layers * per_block
        params += hidden  # final RMSNorm

        if not config.get("tie_weights", True):
            params += hidden * vocab

        return params

    def get_spec(self) -> ArchitectureSpec:
        return self.SPEC
