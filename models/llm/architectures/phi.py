"""Phi architecture reproduction with LongRoPE."""

import logging
from typing import Any

import torch
import torch.nn as nn

from .base import ArchitectureSpec, BaseArchitecture

logger = logging.getLogger(__name__)


class PhiRMSNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return x * norm * self.weight


class LongRoPE(nn.Module):
    def __init__(self, dim: int, base: float = 10000.0, layer_scale: float = 1.0):
        super().__init__()
        self.dim = dim
        self.base = base
        self.layer_scale = layer_scale
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)

    def forward(self, seq_len: int, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
        t = torch.arange(seq_len, device=device).type_as(self.inv_freq)
        freqs = torch.outer(t, self.inv_freq * self.layer_scale)
        emb = torch.cat((freqs, freqs), dim=-1)
        return emb.cos(), emb.sin()


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)


def apply_rotary_pos_emb(q: torch.Tensor, k: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    q = (q * cos) + (rotate_half(q) * sin)
    k = (k * cos) + (rotate_half(k) * sin)
    return q, k


class PhiAttention(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        num_heads: int,
        rope_base: float = 10000.0,
        layer_scale: float = 1.0,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads

        self.q_proj = nn.Linear(hidden_size, num_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(hidden_size, num_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(hidden_size, num_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(num_heads * self.head_dim, hidden_size, bias=False)
        self.rope = LongRoPE(self.head_dim, base=rope_base, layer_scale=layer_scale)

    def forward(self, x: torch.Tensor, _mask: torch.Tensor | None = None) -> torch.Tensor:
        b, t, c = x.size()
        q = self.q_proj(x).view(b, t, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(b, t, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(b, t, self.num_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rope(t, x.device)
        q, k = apply_rotary_pos_emb(q, k, cos, sin)

        attn = torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=True)
        y = attn.transpose(1, 2).contiguous().view(b, t, c)
        return self.o_proj(y)


class PhiMLP(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int):
        super().__init__()
        self.gate_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.up_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.down_proj = nn.Linear(intermediate_size, hidden_size, bias=False)
        self.activation = nn.SiLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(self.activation(self.gate_proj(x)) * self.up_proj(x))


class PhiBlock(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        num_heads: int,
        intermediate_size: int,
        rope_base: float,
        layer_scale: float,
    ):
        super().__init__()
        self.norm1 = PhiRMSNorm(hidden_size)
        self.attn = PhiAttention(hidden_size, num_heads, rope_base, layer_scale)
        self.norm2 = PhiRMSNorm(hidden_size)
        self.mlp = PhiMLP(hidden_size, intermediate_size)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), mask)
        x = x + self.mlp(self.norm2(x))
        return x


class PhiModel(nn.Module):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config
        self.hidden_size = config["hidden_size"]
        self.vocab_size = config["vocab_size"]
        self.num_layers = config["num_layers"]
        self.num_heads = config["num_heads"]
        self.intermediate_size = config["intermediate_size"]
        self.rope_base = config.get("rope_base", 10000.0)
        self.tie_weights = config.get("tie_weights", True)

        rope_bases = config.get("rope_bases")
        if rope_bases is None:
            rope_bases = [self.rope_base] * self.num_layers
        if len(rope_bases) == 1:
            rope_bases = rope_bases * self.num_layers

        self.embed_tokens = nn.Embedding(self.vocab_size, self.hidden_size)
        self.layers = nn.ModuleList([
            PhiBlock(
                self.hidden_size,
                self.num_heads,
                self.intermediate_size,
                self.rope_base,
                rope_bases[i] / self.rope_base,
            )
            for i in range(self.num_layers)
        ])
        self.norm = PhiRMSNorm(self.hidden_size)
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


class PhiArchitecture(BaseArchitecture):
    SPEC = ArchitectureSpec(
        name="phi",
        family="phi",
        paper="Phi-3 Technical Report",
        description="Decoder-only transformer with LongRoPE, dense attention, SwiGLU, and RMSNorm",
        config_path="models/llm/configs/config_phi.yaml",
        parameter_formula=" vocab*hidden + layers*(2*hidden + 4*hidden^2 + 3*hidden*ffn) + hidden",
        key_innovations=["LongRoPE", "dense attention", "SwiGLU", "no biases"],
        supported_features=["longrope", "rope", "swiglu", "rms_norm", "dense_attention", "weight_tying"],
    )

    def build(self, config: dict[str, Any]) -> nn.Module:
        return PhiModel(config)

    def count_parameters(self, config: dict[str, Any]) -> int:
        vocab = config["vocab_size"]
        hidden = config["hidden_size"]
        layers = config["num_layers"]
        ffn = config["intermediate_size"]

        params = vocab * hidden

        per_block = 0
        per_block += 2 * hidden
        per_block += 4 * hidden * hidden
        per_block += 3 * hidden * ffn

        params += layers * per_block
        params += hidden

        if not config.get("tie_weights", True):
            params += hidden * vocab

        return params

    def get_spec(self) -> ArchitectureSpec:
        return self.SPEC
