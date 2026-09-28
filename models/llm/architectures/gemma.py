"""Gemma 2 architecture reproduction."""

import logging
from typing import Any

import torch
import torch.nn as nn

from .base import ArchitectureSpec, BaseArchitecture

logger = logging.getLogger(__name__)


class GemmaRMSNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return x * norm * self.weight


class GemmaRotaryEmbedding(nn.Module):
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


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)


def apply_rotary_pos_emb(q: torch.Tensor, k: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    q = (q * cos) + (rotate_half(q) * sin)
    k = (k * cos) + (rotate_half(k) * sin)
    return q, k


class GemmaAttention(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        num_heads: int,
        num_kv_heads: int,
        head_dim: int,
        window_size: int | None = None,
        rope_base: float = 1000000.0,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = head_dim
        self.num_kv_groups = num_heads // num_kv_heads
        self.window_size = window_size

        self.q_proj = nn.Linear(hidden_size, num_heads * head_dim, bias=False)
        self.k_proj = nn.Linear(hidden_size, num_kv_heads * head_dim, bias=False)
        self.v_proj = nn.Linear(hidden_size, num_kv_heads * head_dim, bias=False)
        self.o_proj = nn.Linear(num_heads * head_dim, hidden_size, bias=False)
        self.rope = GemmaRotaryEmbedding(head_dim, base=rope_base)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        b, t, c = x.size()
        q = self.q_proj(x).view(b, t, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(b, t, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(b, t, self.num_kv_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rope(t, x.device)
        q, k = apply_rotary_pos_emb(q, k, cos[:t], sin[:t])

        if self.num_kv_groups > 1:
            k = k.repeat_interleave(self.num_kv_groups, dim=1)
            v = v.repeat_interleave(self.num_kv_groups, dim=1)

        if self.window_size is not None and self.window_size > 0:
            local_mask = torch.triu(torch.ones(t, t, device=x.device, dtype=torch.bool), diagonal=self.window_size + 1)
            causal_mask = torch.triu(torch.ones(t, t, device=x.device, dtype=torch.bool), diagonal=1)
            mask = local_mask | causal_mask

        attn = torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=True, attn_mask=mask)
        y = attn.transpose(1, 2).contiguous().view(b, t, c)
        return self.o_proj(y)


class GemmaMLP(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int):
        super().__init__()
        self.gate_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.up_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.down_proj = nn.Linear(intermediate_size, hidden_size, bias=False)
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(self.activation(self.gate_proj(x)) * self.up_proj(x))


class GemmaBlock(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        num_heads: int,
        num_kv_heads: int,
        intermediate_size: int,
        rope_base: float,
        window_size: int | None,
        use_local: bool,
    ):
        super().__init__()
        self.norm1 = GemmaRMSNorm(hidden_size)
        self.attn = GemmaAttention(hidden_size, num_heads, num_kv_heads, hidden_size // num_heads, window_size if use_local else None, rope_base)
        self.norm2 = GemmaRMSNorm(hidden_size)
        self.mlp = GemmaMLP(hidden_size, intermediate_size)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), mask)
        x = x + self.mlp(self.norm2(x))
        return x


class GemmaModel(nn.Module):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config
        self.hidden_size = config["hidden_size"]
        self.vocab_size = config["vocab_size"]
        self.num_layers = config["num_layers"]
        self.num_heads = config["num_heads"]
        self.num_kv_heads = config.get("num_kv_heads", config["num_heads"])
        self.intermediate_size = config["intermediate_size"]
        self.rope_base = config.get("rope_base", 1000000.0)
        self.use_local_attention = config.get("use_local_attention", True)
        self.window_size = config.get("window_size", 4096)
        self.tie_weights = config.get("tie_weights", True)

        self.embed_tokens = nn.Embedding(self.vocab_size, self.hidden_size)
        self.layers = nn.ModuleList([
            GemmaBlock(
                self.hidden_size,
                self.num_heads,
                self.num_kv_heads,
                self.intermediate_size,
                self.rope_base,
                self.window_size,
                self.use_local_attention and (i % 2 == 0),
            )
            for i in range(self.num_layers)
        ])
        self.norm = GemmaRMSNorm(self.hidden_size)
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


class GemmaArchitecture(BaseArchitecture):
    SPEC = ArchitectureSpec(
        name="gemma",
        family="gemma",
        paper="Gemma 2: Improving Open Language Models at a Practical Size",
        description="Decoder-only transformer with GeGLU, RoPE base=1e6, RMSNorm, alternating local/global attention",
        config_path="models/llm/configs/config_gemma.yaml",
        parameter_formula=" vocab*hidden + layers*(2*hidden + 4*hidden^2 + 3*hidden*ffn) + hidden",
        key_innovations=["GeGLU", "RoPE 1M", "alternating local/global attention", "no biases"],
        supported_features=["geglu", "rope", "rms_norm", "gqa", "sliding_window", "weight_tying"],
    )

    def build(self, config: dict[str, Any]) -> nn.Module:
        return GemmaModel(config)

    def count_parameters(self, config: dict[str, Any]) -> int:
        vocab = config["vocab_size"]
        hidden = config["hidden_size"]
        layers = config["num_layers"]
        heads = config["num_heads"]
        kv_heads = config.get("num_kv_heads", heads)
        ffn = config["intermediate_size"]
        head_dim = hidden // heads

        params = vocab * hidden

        per_block = 0
        per_block += 2 * hidden  # 2 RMSNorm
        # Attention: Q + K + V + O
        q_params = hidden * hidden
        k_params = kv_heads * head_dim * hidden
        v_params = kv_heads * head_dim * hidden
        o_params = hidden * hidden
        per_block += q_params + k_params + v_params + o_params
        # MLP: gate + up + down (GeGLU)
        per_block += 3 * hidden * ffn

        params += layers * per_block
        params += hidden  # final RMSNorm

        if not config.get("tie_weights", True):
            params += hidden * vocab

        return params

    def get_spec(self) -> ArchitectureSpec:
        return self.SPEC
