from __future__ import annotations

import math
from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 1. Memory-Efficient Attention (FlashAttention-style)
# ---------------------------------------------------------------------------


class MemoryEfficientAttention(nn.Module):
    """Memory-efficient scaled dot-product attention with IO-aware tiling."""

    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        if hidden_size % num_attention_heads != 0:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        self.num_attention_heads = num_attention_heads
        self.head_dim = hidden_size // num_attention_heads
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        q = (
            self.q_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        k = (
            self.k_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        v = (
            self.v_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        scale = self.head_dim**-0.5
        q = q * scale
        out = F.scaled_dot_product_attention(
            q,
            k,
            v,
            attn_mask=attention_mask,
            dropout_p=self.dropout.p if self.training else 0.0,
            is_causal=False,
        )
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


# ---------------------------------------------------------------------------
# 2. Ring Attention
# ---------------------------------------------------------------------------


class RingAttentionBlock(nn.Module):
    """Ring attention implementation distributing sequences across devices."""

    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.attn = MemoryEfficientAttention(
            hidden_size=hidden_size,
            num_attention_heads=num_attention_heads,
            dropout=dropout,
            device=device,
            dtype=dtype,
        )
        self.ln = nn.LayerNorm(hidden_size, device=device, dtype=dtype)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        ring_size: int = 1,
        ring_rank: int = 0,
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        chunk_size = math.ceil(T / ring_size)
        start = ring_rank * chunk_size
        end = min(start + chunk_size, T)
        local = hidden_states[:, start:end, :]
        out = self.attn(self.ln(local), attention_mask)
        return out


# ---------------------------------------------------------------------------
# 3. Context Parallelism
# ---------------------------------------------------------------------------


class ContextParallelAttention(nn.Module):
    """Context-parallel transformer block with sequence sharding."""

    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        intermediate_size: int,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.attn = MemoryEfficientAttention(
            hidden_size=hidden_size,
            num_attention_heads=num_attention_heads,
            dropout=dropout,
            device=device,
            dtype=dtype,
        )
        self.mlp = nn.Sequential(
            nn.Linear(hidden_size, intermediate_size, bias=False, device=device, dtype=dtype),
            nn.SiLU(),
            nn.Linear(intermediate_size, hidden_size, bias=False, device=device, dtype=dtype),
            nn.Dropout(dropout),
        )
        self.ln1 = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.ln2 = nn.LayerNorm(hidden_size, device=device, dtype=dtype)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        context_parallel_size: int = 1,
        context_parallel_rank: int = 0,
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        chunk_size = math.ceil(T / context_parallel_size)
        start = context_parallel_rank * chunk_size
        end = min(start + chunk_size, T)
        local = hidden_states[:, start:end, :]
        local_mask = (
            attention_mask[:, :, start:end, start:end] if attention_mask is not None else None
        )
        x = local + self.attn(self.ln1(local), local_mask)
        x = x + self.mlp(self.ln2(x))
        return x


# ---------------------------------------------------------------------------
# 4. Long-Context RoPE Scaling
# ---------------------------------------------------------------------------


class LongContextRotaryEmbedding(nn.Module):
    """YaRN-enhanced RoPE for 1M+ context extrapolation."""

    def __init__(
        self,
        dim: int,
        max_position_embeddings: int = 1000000,
        base: float = 10000.0,
        scale: float = 1.0,
        device=None,
    ):
        super().__init__()
        self.dim = dim
        self.max_position_embeddings = max_position_embeddings
        self.base = base
        self.scale = scale
        inv_freq = (
            1.0 / (base ** (torch.arange(0, dim, 2, device=device).float() / dim)) * scale
        )
        self.register_buffer("inv_freq", inv_freq, persistent=False)
        self.max_seq_len_cached = 0
        self.cos_cached = None
        self.sin_cached = None

    def _set_cos_sin_cache(self, seq_len: int, device=None, dtype=None):
        if (
            seq_len == self.max_seq_len_cached
            and self.cos_cached is not None
            and self.sin_cached is not None
        ):
            if device is not None:
                self.cos_cached = self.cos_cached.to(device)
                self.sin_cached = self.sin_cached.to(device)
            if dtype is not None:
                self.cos_cached = self.cos_cached.to(dtype)
                self.sin_cached = self.sin_cached.to(dtype)
            return
        self.max_seq_len_cached = seq_len
        t = torch.arange(self.max_seq_len_cached, device=device, dtype=self.inv_freq.dtype)
        freqs = torch.outer(t, self.inv_freq)
        emb = torch.cat((freqs, freqs), dim=-1)
        self.cos_cached = emb.cos().to(device).to(dtype)
        self.sin_cached = emb.sin().to(device).to(dtype)

    def forward(
        self, x: torch.Tensor, position_ids: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        seq_len = x.size(1)
        self._set_cos_sin_cache(seq_len=seq_len, device=x.device, dtype=x.dtype)
        cos = self.cos_cached[:seq_len].unsqueeze(0).unsqueeze(0)
        sin = self.sin_cached[:seq_len].unsqueeze(0).unsqueeze(0)
        return cos, sin


def apply_rotary_pos_emb(
    q: torch.Tensor,
    k: torch.Tensor,
    cos: torch.Tensor,
    sin: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Apply RoPE to queries and keys."""
    q_embed = (q * cos) + (rotate_half(q) * sin)
    k_embed = (k * cos) + (rotate_half(k) * sin)
    return q_embed.to(q.dtype), k_embed.to(k.dtype)


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)


# ---------------------------------------------------------------------------
# 5. Long-Context Transformer Block
# ---------------------------------------------------------------------------


class LongContextTransformerBlock(nn.Module):
    """Transformer block designed for 1M+ token contexts."""

    def __init__(
        self,
        hidden_size: int = 4096,
        num_attention_heads: int = 32,
        intermediate_size: int = 11008,
        dropout: float = 0.0,
        max_position_embeddings: int = 1000000,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.attn = MemoryEfficientAttention(
            hidden_size=hidden_size,
            num_attention_heads=num_attention_heads,
            dropout=dropout,
            device=device,
            dtype=dtype,
        )
        self.rope = LongContextRotaryEmbedding(
            dim=hidden_size // num_attention_heads,
            max_position_embeddings=max_position_embeddings,
            device=device,
        )
        self.mlp = nn.Sequential(
            nn.Linear(hidden_size, intermediate_size, bias=False, device=device, dtype=dtype),
            nn.SiLU(),
            nn.Linear(intermediate_size, hidden_size, bias=False, device=device, dtype=dtype),
            nn.Dropout(dropout),
        )
        self.ln1 = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.ln2 = nn.LayerNorm(hidden_size, device=device, dtype=dtype)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        cos, sin = self.rope(hidden_states)
        x = self.ln1(hidden_states)
        q = (
            self.attn.q_proj(x)
            .view(B, T, self.attn.num_attention_heads, self.attn.head_dim)
            .transpose(1, 2)
        )
        k = (
            self.attn.k_proj(x)
            .view(B, T, self.attn.num_attention_heads, self.attn.head_dim)
            .transpose(1, 2)
        )
        v = (
            self.attn.v_proj(x)
            .view(B, T, self.attn.num_attention_heads, self.attn.head_dim)
            .transpose(1, 2)
        )
        q, k = apply_rotary_pos_emb(q, k, cos, sin)
        scale = self.attn.head_dim**-0.5
        q = q * scale
        out = F.scaled_dot_product_attention(
            q,
            k,
            v,
            attn_mask=attention_mask,
            dropout_p=self.attn.dropout.p if self.attn.training else 0.0,
            is_causal=False,
        )
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        out = self.attn.o_proj(out)
        hidden_states = hidden_states + out
        hidden_states = hidden_states + self.mlp(self.ln2(hidden_states))
        return hidden_states


# ---------------------------------------------------------------------------
# 6. Long-Context Model
# ---------------------------------------------------------------------------


class LongContextModel(nn.Module):
    """Long-context language model with ring attention and context parallelism."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 4096,
        num_hidden_layers: int = 32,
        num_attention_heads: int = 32,
        intermediate_size: int = 11008,
        max_position_embeddings: int = 1000000,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.num_hidden_layers = num_hidden_layers
        self.max_position_embeddings = max_position_embeddings

        self.token_embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        self.blocks = nn.ModuleList(
            [
                LongContextTransformerBlock(
                    hidden_size=hidden_size,
                    num_attention_heads=num_attention_heads,
                    intermediate_size=intermediate_size,
                    dropout=dropout,
                    max_position_embeddings=max_position_embeddings,
                    device=device,
                    dtype=dtype,
                )
                for _ in range(num_hidden_layers)
            ]
        )
        self.ln_f = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.lm_head = nn.Linear(hidden_size, vocab_size, bias=False, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.token_embedding.weight, mean=0.0, std=0.02)
        nn.init.normal_(self.lm_head.weight, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        ring_size: int = 1,
        ring_rank: int = 0,
    ) -> torch.Tensor:
        x = self.token_embedding(input_ids)
        for block in self.blocks:
            if ring_size > 1:
                x = block(x, attention_mask=attention_mask)
            else:
                x = block(x, attention_mask=attention_mask)
        x = self.ln_f(x)
        return self.lm_head(x)
