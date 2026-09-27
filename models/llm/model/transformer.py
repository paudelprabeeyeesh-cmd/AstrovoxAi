import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple


class RMSNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float = 1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.eps = eps

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        variance = hidden_states.pow(2).mean(-1, keepdim=True)
        hidden_states = hidden_states * torch.rsqrt(variance + self.eps)
        return self.weight * hidden_states


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)


def apply_rotary_pos_emb(q: torch.Tensor, k: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor, position_ids: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
    q_embed = (q * cos) + (rotate_half(q) * sin)
    k_embed = (k * cos) + (rotate_half(k) * sin)
    return q_embed, k_embed


class RotaryEmbedding(nn.Module):
    def __init__(self, dim: int, max_position_embeddings: int = 2048, base: float = 10000.0, device=None):
        super().__init__()
        self.dim = dim
        self.max_position_embeddings = max_position_embeddings
        self.base = base
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float().to(device) / dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)
        self.max_seq_len_cached = 0
        self.cos_cached = None
        self.sin_cached = None

    def _set_cos_sin_cache(self, seq_len: int, device=None, dtype=None):
        if seq_len == self.max_seq_len_cached and self.cos_cached is not None and self.sin_cached is not None:
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

    def forward(self, x: torch.Tensor, position_ids: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        seq_len = x.size(2) if x.dim() == 4 else x.size(1)
        self._set_cos_sin_cache(seq_len=seq_len + 1, device=x.device, dtype=x.dtype)
        if position_ids is not None:
            cos = self.cos_cached[position_ids].unsqueeze(1)
            sin = self.sin_cached[position_ids].unsqueeze(1)
        else:
            cos = self.cos_cached[:seq_len].unsqueeze(0).unsqueeze(0)
            sin = self.sin_cached[:seq_len].unsqueeze(0).unsqueeze(0)
        return cos.to(x.dtype), sin.to(x.dtype)


def _flash_attention_forward(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
    dropout_p: float = 0.0,
    training: bool = False,
    scale: Optional[float] = None,
) -> torch.Tensor:
    if hasattr(F, 'scaled_dot_product_attention'):
        if scale is not None:
            query = query * scale
        return F.scaled_dot_product_attention(query, key, value, attn_mask=attention_mask, dropout_p=dropout_p if training else 0.0)
    return _eager_attention_forward(query, key, value, attention_mask, dropout_p, training, scale)


def _eager_attention_forward(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
    dropout_p: float = 0.0,
    training: bool = False,
    scale: Optional[float] = None,
) -> torch.Tensor:
    if scale is None:
        scale = 1.0 / math.sqrt(query.size(-1))
    attn_weights = (query @ key.transpose(-2, -1)) * scale
    if attention_mask is not None:
        attn_weights = attn_weights + attention_mask
    attn_weights = F.softmax(attn_weights, dim=-1, dtype=torch.float32).to(query.dtype)
    attn_weights = F.dropout(attn_weights, p=dropout_p, training=training)
    return attn_weights @ value


class CausalSelfAttention(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        max_position_embeddings: int = 2048,
        rope_theta: float = 10000.0,
        dropout: float = 0.0,
        attention_bias: bool = False,
    ):
        super().__init__()
        if hidden_size % num_attention_heads != 0:
            raise ValueError(f"hidden_size {hidden_size} must be divisible by num_attention_heads {num_attention_heads}")
        self.num_attention_heads = num_attention_heads
        self.head_dim = hidden_size // num_attention_heads
        self.scale = self.head_dim ** -0.5

        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=attention_bias)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=attention_bias)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=attention_bias)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=attention_bias)
        self.dropout = nn.Dropout(dropout)

        self.rotary_emb = RotaryEmbedding(self.head_dim, max_position_embeddings=max_position_embeddings, base=rope_theta)
        self.use_flash = hasattr(F, 'scaled_dot_product_attention')
        self.use_kv_cache = False
        self._cache = KVCache()

    def forward(
        self,
        hidden_states: torch.Tensor,
        position_ids: Optional[torch.Tensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        use_gradient_checkpointing: bool = False,
    ) -> torch.Tensor:
        B, T, C = hidden_states.size()
        q = self.q_proj(hidden_states).view(B, T, self.num_attention_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(hidden_states).view(B, T, self.num_attention_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(hidden_states).view(B, T, self.num_attention_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rotary_emb(v, position_ids=position_ids)
        q, k = apply_rotary_pos_emb(q, k, cos, sin, position_ids=position_ids)

        if self.use_kv_cache:
            self._cache.update(k, v)
            k, v = self._cache.get()

        if self.use_flash:
            attn_output = _flash_attention_forward(
                query=q,
                key=k,
                value=v,
                attention_mask=attention_mask,
                dropout_p=self.dropout.p if self.training else 0.0,
                training=self.training,
                scale=self.scale,
            )
        else:
            if attention_mask is None:
                causal_mask = torch.triu(torch.ones(T, T, device=hidden_states.device, dtype=torch.bool), diagonal=1)
                attention_mask = torch.masked_fill(torch.zeros(T, T, device=hidden_states.device, dtype=torch.float32), causal_mask, float("-inf"))
                attention_mask = attention_mask.unsqueeze(0).unsqueeze(0)
            attn_output = _eager_attention_forward(q, k, v, attention_mask=attention_mask, dropout_p=self.dropout.p if self.training else 0.0, training=self.training, scale=self.scale)

        out = attn_output.transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


class KVCache:
    def __init__(self):
        self.key_cache: Optional[torch.Tensor] = None
        self.value_cache: Optional[torch.Tensor] = None
        self.cache_len = 0

    def update(self, key: torch.Tensor, value: torch.Tensor):
        if self.key_cache is None:
            self.key_cache = key
            self.value_cache = value
        else:
            self.key_cache = torch.cat([self.key_cache, key], dim=2)
            self.value_cache = torch.cat([self.value_cache, value], dim=2)
        self.cache_len = self.key_cache.size(2)

    def get(self):
        return self.key_cache, self.value_cache

    def clear(self):
        self.key_cache = None
        self.value_cache = None
        self.cache_len = 0


class SwiGLUMLP(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, dropout: float = 0.0, bias: bool = False, device=None, dtype=None):
        super().__init__()
        self.gate_proj = nn.Linear(hidden_size, intermediate_size, bias=bias, device=device, dtype=dtype)
        self.up_proj = nn.Linear(hidden_size, intermediate_size, bias=bias, device=device, dtype=dtype)
        self.down_proj = nn.Linear(intermediate_size, hidden_size, bias=bias, device=device, dtype=dtype)
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)

    @torch.no_grad()
    def _reset_parameters(self):
        for module in [self.gate_proj, self.up_proj, self.down_proj]:
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        hidden_states = self.down_proj(self.act(self.gate_proj(hidden_states)) * self.up_proj(hidden_states))
        return self.dropout(hidden_states)


class TransformerBlock(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        intermediate_size: int,
        max_position_embeddings: int = 2048,
        rope_theta: float = 10000.0,
        rms_norm_eps: float = 1e-5,
        dropout: float = 0.0,
        activation: str = "swiglu",
        attention_bias: bool = False,
        mlp_bias: bool = False,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.ln_1 = RMSNorm(hidden_size, eps=rms_norm_eps).to(device=device, dtype=dtype)
        self.attn = CausalSelfAttention(
            hidden_size=hidden_size,
            num_attention_heads=num_attention_heads,
            max_position_embeddings=max_position_embeddings,
            rope_theta=rope_theta,
            dropout=dropout,
            attention_bias=attention_bias,
        )
        self.ln_2 = RMSNorm(hidden_size, eps=rms_norm_eps).to(device=device, dtype=dtype)
        if activation == "swiglu":
            self.mlp = SwiGLUMLP(hidden_size, intermediate_size, dropout=dropout, bias=mlp_bias, device=device, dtype=dtype)
        else:
            self.mlp = nn.Sequential(
                nn.Linear(hidden_size, intermediate_size, bias=mlp_bias, device=device, dtype=dtype),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(intermediate_size, hidden_size, bias=mlp_bias, device=device, dtype=dtype),
                nn.Dropout(dropout),
            ).to(device=device, dtype=dtype)

    def forward(
        self,
        hidden_states: torch.Tensor,
        position_ids: Optional[torch.Tensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        use_gradient_checkpointing: bool = False,
    ) -> torch.Tensor:
        residual = hidden_states
        if use_gradient_checkpointing and self.training:
            hidden_states = torch.utils.checkpoint.checkpoint(self.ln_1, hidden_states, use_reentrant=False)
            hidden_states = torch.utils.checkpoint.checkpoint(self.attn, hidden_states, position_ids=position_ids, attention_mask=attention_mask, use_reentrant=False)
        else:
            hidden_states = self.ln_1(hidden_states)
            hidden_states = self.attn(hidden_states, position_ids=position_ids, attention_mask=attention_mask)
        hidden_states = residual + hidden_states

        residual = hidden_states
        if use_gradient_checkpointing and self.training:
            hidden_states = torch.utils.checkpoint.checkpoint(self.ln_2, hidden_states, use_reentrant=False)
            hidden_states = torch.utils.checkpoint.checkpoint(self.mlp, hidden_states, use_reentrant=False)
        else:
            hidden_states = self.ln_2(hidden_states)
            hidden_states = self.mlp(hidden_states)
        hidden_states = residual + hidden_states
        return hidden_states


class OutputLayer(nn.Module):
    def __init__(self, hidden_size: int, vocab_size: int, tie_weights: bool = True, device=None, dtype=None):
        super().__init__()
        self.lm_head = nn.Linear(hidden_size, vocab_size, bias=False, device=device, dtype=dtype)
        self.tie_weights = tie_weights

    @torch.no_grad()
    def _reset_parameters(self):
        nn.init.normal_(self.lm_head.weight, mean=0.0, std=0.02)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        return self.lm_head(hidden_states)
