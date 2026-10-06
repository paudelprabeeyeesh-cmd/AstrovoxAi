"""Transformer components: attention, feed-forward blocks, and full transformer.

The attention implementation uses grouped-query attention, which lets several
query heads share one key/value head. This is how most current open models cut
the memory cost of the KV cache during inference without hurting quality.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

from astrovox.autograd.function import Function
from astrovox.nn.layernorm import LayerNorm
from astrovox.nn.linear import Activation, Embedding, Linear
from astrovox.nn.module import Module, init_zeros, parameter
from astrovox.nn.rmsnorm import RMSNorm
from astrovox.ops.activation import gelu, softmax
from astrovox.ops.attention import chunked_attention
from astrovox.ops.math import add, div, matmul, mul, neg, sqrt
from astrovox.tensor.dtype import DEFAULT
from astrovox.tensor.shape import Shape
from astrovox.tensor.tensor import Tensor


class MaskedSoftmax(Function):
    """Softmax with an optional causal or padding mask.

    Numerically stable: subtracts the row maximum before exponentiating. The
    mask is applied in log-space (masked positions get ``-inf``) so the mask
    interacts correctly with the maximum.
    """

    name = "masked_softmax"

    @staticmethod
    def forward(ctx, scores: Tensor, mask: Tensor | None = None, causal: bool = False, axis: int = -1):
        x = scores.numpy().astype(np.float64)
        if causal:
            seq = x.shape[-1]
            row = np.arange(seq)[:, None]
            col = np.arange(seq)[None, :]
            mask = np.where(col > row, -np.inf, 0.0)
        if mask is not None:
            mask = mask.numpy().astype(np.float64)
            x = np.where(mask == 0.0, -np.inf, x)
        # Reduce in the requested axis (normalize over last axis by default).
        ax = mask_axis = axis if axis >= 0 else x.ndim + axis
        maximum = np.max(x, axis=mask_axis, keepdims=True)
        e = np.exp(x - maximum)
        out = e / np.maximum(e.sum(axis=mask_axis, keepdims=True), 1e-300)
        result = Tensor.from_numpy(out.astype(scores.dtype.np_dtype), scores.dtype, scores.device)
        ctx.save(scores=scores, mask=mask, causal=causal, axis=mask_axis, maximum=maximum)
        return result.requires_grad_(scores.requires_grad)

    @staticmethod
    def backward(ctx, grad_output: Tensor):
        scores = ctx.load("scores")
        mask, causal, axis, maximum = ctx.load("mask"), ctx.load("causal"), ctx.load("axis"), ctx.load("maximum")
        attn = ctx.load("attn")
        grad = grad_output.numpy().astype(np.float64)
        attn = attn.numpy().astype(np.float64)
        d_scores = attn * (grad - (attn * grad).sum(axis=axis, keepdims=True))
        return Tensor.from_numpy(d_scores.astype(scores.dtype.np_dtype), scores.dtype, scores.device), None, None, None


class MultiHeadAttention(Module):
    """Multi-head self-attention with grouped-query attention support.

    If ``gqa_groups`` equals the head count the layer is full multi-head
    attention; if it is smaller, GQA lets several query heads share a key/value
    head to cut KV cache memory.
    """

    def __init__(
        self,
        embed_dim: int,
        num_heads: int,
        gqa_groups: int | None = None,
        dropout: float = 0.0,
        bias: bool = True,
        causal: bool = True,
        dtype: Any = DEFAULT,
    ) -> None:
        super().__init__()
        if embed_dim % num_heads != 0:
            raise ValueError(f"embed_dim {embed_dim} must be divisible by num_heads {num_heads}")
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.gqa_groups = gqa_groups if gqa_groups is not None else num_heads
        self.dropout = dropout
        self.causal = causal
        if num_heads < self.gqa_groups:
            raise ValueError("num_heads must be >= gqa_groups")
        total_q = num_heads * self.head_dim
        total_kv = self.gqa_groups * self.head_dim
        self.q_proj = Linear(embed_dim, total_q, bias=bias)
        self.k_proj = Linear(embed_dim, total_kv, bias=bias)
        self.v_proj = Linear(embed_dim, total_kv, bias=bias)
        self.out_proj = Linear(total_q, embed_dim, bias=bias)

    def _reshape_heads(self, x: Tensor, batch: int) -> Tensor:
        seq = x.shape.dims[-2]
        return x.reshape((batch, seq, self.num_heads, self.head_dim)).transpose(1, 2)

    def _transpose_kv_heads(self, x: Tensor, batch: int) -> Tensor:
        seq = x.shape.dims[-2]
        return x.reshape((batch, seq, self.gqa_groups, self.head_dim)).transpose(1, 2)

    def forward(
        self,
        query: Tensor,
        key: Tensor | None = None,
        value: Tensor | None = None,
        attn_mask: Tensor | None = None,
        training: bool = True,
    ) -> Tensor:
        key = key if key is not None else query
        value = value if value is not None else query
        batch, seq_q, _ = query.shape.dims[0], query.shape.dims[-2], query.shape.dims[-1]
        q = self._reshape_heads(self.q_proj(query), batch)
        k = self._transpose_kv_heads(self.k_proj(key), batch)
        v = self._transpose_kv_heads(self.v_proj(value), batch)
        if self.causal and attn_mask is None:
            attn_mask = Tensor.from_numpy(np.tril(np.ones((seq_q, seq_q))).astype(np.float32), q.dtype, q.device)
        scores = matmul(q, k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
        if attn_mask is not None:
            scores = scores + (Tensor.from_numpy(
                np.where(attn_mask.numpy() == 0.0, -np.inf, 0.0), q.dtype, q.device))
        attn = softmax(scores, -1)
        if self.dropout and training:
            attn = attn * Tensor.from_numpy(
                (np.random.rand(*attn.shape.dims) >= self.dropout).astype(np.float32) / (1.0 - self.dropout),
                attn.dtype, attn.device)
        out = matmul(attn, v)
        out = out.transpose(1, 2).reshape((batch, seq_q, self.embed_dim))
        return self.out_proj(out)


class RepeatKV(Function):
    """Repeat key/value heads so query heads can share KV heads (GQA/ MQA)."""

    name = "repeat_kv"

    @staticmethod
    def forward(ctx, k: Tensor, v: Tensor, num_heads: int, gqa_groups: int):
        n_rep = num_heads // gqa_groups
        if n_rep * gqa_groups != num_heads:
            raise ValueError("num_heads must be a multiple of gqa_groups")
        def repeat(t: np.ndarray, groups: int) -> np.ndarray:
            batch, heads, seq, dim = t.shape
            return t.reshape(batch, groups, n_rep, seq, dim).repeat(n_rep, axis=1).reshape(batch, num_heads, seq, dim)
        k_out = repeat(k.numpy(), gqa_groups)
        v_out = repeat(v.numpy(), gqa_groups)
        ctx.save(num_heads=num_heads, gqa_groups=gqa_groups)
        return (Tensor.from_numpy(k_out.astype(k.dtype.np_dtype), k.dtype, k.device),
                Tensor.from_numpy(v_out.astype(v.dtype.np_dtype), v.dtype, v.device))

    @staticmethod
    def backward(ctx, grad_k: Tensor, grad_v: Tensor):
        num_heads, gqa_groups = ctx.load("num_heads"), ctx.load("gqa_groups")
        n_rep = num_heads // gqa_groups
        def unrepeat(t: np.ndarray, groups: int) -> np.ndarray:
            return t.reshape(grad_k.shape[0], groups, n_rep, t.shape[2], t.shape[3]).sum(axis=2)
        return Tensor.from_numpy(unrepeat(grad_k.numpy(), gqa_groups).astype(grad_k.dtype.np_dtype), grad_k.dtype, grad_k.device), None


class FeedForward(Module):
    """A two-layer feed-forward network with an internal activation.

    Matches the common transformer FFN shape ``(embed, hidden, embed)``.
    """

    def __init__(self, embed_dim: int, hidden_dim: int, activation: Any = gelu, dropout: float = 0.0) -> None:
        super().__init__()
        self.fc1 = Linear(embed_dim, hidden_dim)
        self.fc2 = Linear(hidden_dim, embed_dim)
        self.act = Activation(activation, getattr(activation, "__name__", "activation"))
        self.dropout = Dropout(dropout) if dropout > 0.0 else None

    def forward(self, x: Tensor) -> Tensor:
        x = self.fc1(x)
        x = self.act(x)
        if self.dropout is not None:
            x = self.dropout(x)
        return self.fc2(x)


class TransformerBlock(Module):
    """A single transformer block with pre-norm residuals."""

    def __init__(
        self,
        embed_dim: int,
        num_heads: int,
        gqa_groups: int | None = None,
        ff_dim: int | None = None,
        dropout: float = 0.0,
        causal: bool = True,
    ) -> None:
        super().__init__()
        self.causal = causal
        self.self_attn = MultiHeadAttention(embed_dim, num_heads, gqa_groups=gqa_groups, dropout=dropout, causal=causal)
        self.norm1 = LayerNorm((embed_dim,), eps=1e-5)
        self.ff = FeedForward(embed_dim, ff_dim if ff_dim is not None else embed_dim * 4, dropout=dropout)
        self.norm2 = LayerNorm((embed_dim,), eps=1e-5)
        self.dropout = Dropout(dropout) if dropout > 0.0 else None

    def forward(self, x: Tensor, attn_mask: Tensor | None = None) -> Tensor:
        h = self.norm1(x)
        h = self.self_attn(h, attn_mask=attn_mask, training=self.training)
        if self.dropout is not None:
            h = self.dropout(h)
        x = x + h
        h = self.norm2(x)
        h = self.ff(h)
        if self.dropout is not None:
            h = self.dropout(h)
        return x + h


class PositionalEncoding(Module):
    """Learned positional embeddings (simpler and more robust than sinusoidal)."""

    def __init__(self, vocab_size: int, max_seq_len: int, embed_dim: int, dropout: float = 0.0) -> None:
        super().__init__()
        self.dropout = Dropout(dropout) if dropout > 0.0 else None
        self.pe = parameter(np.zeros((max_seq_len, embed_dim), dtype=np.float32), "positional_encoding")

    def forward(self, x: Tensor, seq_len: int | None = None) -> Tensor:
        seq_len = seq_len if seq_len is not None else x.shape.dims[-2]
        pe = self.pe[:seq_len]
        out = x + Tensor.from_numpy(pe[np.newaxis, :, :], x.dtype, x.device)
        if self.dropout is not None and self.training:
            out = self.dropout(out)
        return out


class _Dropout(Module):
    """Dropout wrapper used inside TransformerBlock."""

    def __init__(self, p: float = 0.5, seed: int | None = None) -> None:
        super().__init__()
        if not 0.0 <= p < 1.0:
            raise ValueError(f"Dropout probability must be in [0, 1), got {p}")
        self.p = p
        self._rng = np.random.default_rng(seed)
        self._mask: np.ndarray | None = None

    def forward(self, x: Tensor) -> Tensor:
        if not self.training or self.p == 0.0:
            return x
        mask = (self._rng.random(x.shape.dims) >= self.p).astype(x.dtype.np_dtype) / (1.0 - self.p)
        self._mask = mask
        return mul(x, Tensor.from_numpy(mask, x.dtype))


def Dropout(p: float = 0.5, seed: int | None = None) -> Module:
    return _Dropout(p, seed)


class TransformerEncoder(Module):
    """A stack of transformer encoder blocks."""

    def __init__(
        self,
        vocab_size: int,
        embed_dim: int,
        num_heads: int,
        num_layers: int,
        ff_dim: int | None = None,
        dropout: float = 0.0,
        causal: bool = True,
        gqa_groups: int | None = None,
    ) -> None:
        super().__init__()
        self.embedding = Embedding(vocab_size, embed_dim)
        self.pos = PositionalEncoding(vocab_size, 4096, embed_dim, dropout=dropout)
        self.layers = ModuleList([TransformerBlock(embed_dim, num_heads, gqa_groups=gqa_groups,
                                                     ff_dim=ff_dim, dropout=dropout, causal=causal)
                                   for _ in range(num_layers)])
        self.norm = LayerNorm((embed_dim,), eps=1e-5)
        self.dropout = Dropout(dropout) if dropout > 0.0 else None

    def forward(self, x: Tensor, attn_mask: Tensor | None = None) -> Tensor:
        x = self.embedding(x) * math.sqrt(x.shape.dims[-1])
        if self.dropout is not None:
            x = self.dropout(x)
        x = self.pos(x)
        for layer in self.layers:
            x = layer(x, attn_mask=attn_mask)
        return self.norm(x)


class ModuleList(Module):
    """A flexible container for storing submodules."""

    def __init__(self, modules: Sequence[Module] = ()) -> None:
        super().__init__()
        for i, mod in enumerate(modules):
            self.add_module(str(i), mod)

    def __iter__(self):
        return iter(self._modules.values())

    def append(self, module: Module) -> None:
        self.add_module(str(len(self._modules)), module)

    def add_module(self, name: str, module: Module) -> None:
        self._modules[name] = module


class Embedding(Module):
    """A lookup table mapping integer indices to learned vectors."""

    def __init__(self, num_embeddings: int, embedding_dim: int) -> None:
        super().__init__()
        if num_embeddings <= 0 or embedding_dim <= 0:
            raise ValueError("Embedding requires positive num_embeddings and embedding_dim")
        self.num_embeddings = num_embeddings
        self.embedding_dim = embedding_dim
        self.weight = parameter(np.zeros((num_embeddings, embedding_dim), dtype=np.float32), "weight")


def _check_attention_inputs(q: Tensor, k: Tensor, v: Tensor) -> tuple[int, int, int, int]:
    if q.ndim != 4 or k.ndim != 4 or v.ndim != 4:
        raise ValueError(f"attention expects 4-D inputs, got {q.ndim}-D, {k.ndim}-D, {v.ndim}-D")
    if q.shape.dims[0] != k.shape.dims[0] or q.shape.dims[0] != v.shape.dims[0]:
        raise ValueError("batch dimensions of q, k and v must match")
    return q.shape.dims[0], q.shape.dims[1], q.shape.dims[2], q.shape.dims[-1]
