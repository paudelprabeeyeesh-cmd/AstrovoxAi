"""Transformer components: attention, feed-forward blocks, and full blocks.

The attention implementation uses grouped-query attention, which lets several
query heads share one key/value head. This is how most current open models cut
the memory cost of the KV cache during inference without hurting quality.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

from astrovox.nn.layernorm import LayerNorm
from astrovox.nn.linear import Activation, Linear
from astrovox.nn.module import Module, init_zeros, parameter
from astrovox.nn.rmsnorm import RMSNorm
from astrovox.ops.activation import gelu, softmax
from astrovox.ops.math import add, div, matmul, mul, neg, sqrt
from astrovox.tensor.shape import Shape
from astrovox.tensor.tensor import Tensor


def _attention(q: Tensor, k: Tensor, v: Tensor, causal: bool = True, mask: Tensor | None = None) -> Tensor:
    """Compute scaled dot-product attention over the last two dimensions.

    Args:
        q: query tensor ``(batch, heads, seq, head_dim)``.
        k: key tensor ``(batch, heads_kv, seq, head_dim)``.
        v: value tensor ``(batch, heads_kv, seq, head_dim)``.
        causal: whether to mask future positions.
        mask: optional additive mask broadcastable to the score shape.
    """
    head_dim = q.shape.dims[-1]
    scale = 1.0 / math.sqrt(head_dim)

    scores = matmul(q, k.transpose(-1, -2)) * scale
    weights = _softmax_with_mask(scores, causal=causal, mask=mask)
    return matmul(weights, v)


def _softmax_with_mask(scores: Tensor, causal: bool, mask: Tensor | None) -> Tensor:
    """Apply softmax with optional causal and additive masking."""
    if not causal and mask is None:
        return softmax(scores, axis=-1)

    from astrovox.ops.activation import Softmax

    array = scores.numpy().copy()
    if causal and array.ndim >= 2:
        seq_len = array.shape[-2]
        array = array + np.triu(np.full((seq_len, seq_len), -np.inf, dtype=array.dtype), k=1)
    if mask is not None:
        array = array + mask.numpy()
    # Rows that are fully masked would produce NaN; give them a uniform
    # distribution instead so a padded batch still yields finite gradients.
    finite = np.isfinite(array)
    array = np.where(finite, array, -1e30)
    shifted = array - array.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    out = exp / exp.sum(axis=-1, keepdims=True)
    return Tensor.from_numpy(out, scores.dtype, scores.device)


class MultiHeadAttention(Module):
    """Multi-head attention with optional grouped queries.

    Args:
        d_model: model width.
        num_heads: number of query heads.
        num_kv_heads: key/value heads; defaults to ``num_heads``. Values below
            the query head count enable grouped-query attention.
        dropout: attention dropout probability.
        bias: whether projections learn a bias.
        causal: whether to apply a causal mask.
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int,
        num_kv_heads: int | None = None,
        dropout: float = 0.0,
        bias: bool = True,
        causal: bool = True,
    ) -> None:
        super().__init__()
        if d_model % num_heads:
            raise ValueError(f"d_model {d_model} must be divisible by num_heads {num_heads}")
        kv_heads = num_kv_heads or num_heads
        if num_heads % kv_heads:
            raise ValueError(f"num_heads {num_heads} must be divisible by num_kv_heads {kv_heads}")

        self.d_model = d_model
        self.num_heads = num_heads
        self.num_kv_heads = kv_heads
        self.head_dim = d_model // num_heads
        self.causal = causal
        self.dropout = dropout

        self.q_proj = Linear(d_model, num_heads * self.head_dim, bias=bias)
        self.k_proj = Linear(d_model, kv_heads * self.head_dim, bias=bias)
        self.v_proj = Linear(d_model, kv_heads * self.head_dim, bias=bias)
        self.o_proj = Linear(num_heads * self.head_dim, d_model, bias=bias)

    def _split_heads(self, x: Tensor, batch: int, seq: int, heads: int) -> Tensor:
        """Reshape a projection output into ``(batch, heads, seq, head_dim)``."""
        return x.reshape(batch, seq, heads, self.head_dim).transpose(1, 2)

    def forward(self, x: Tensor, mask: Tensor | None = None) -> Tensor:
        """Run self-attention over ``x``."""
        if x.ndim != 3:
            raise ValueError(f"MultiHeadAttention expects (batch, seq, d_model), got {tuple(x.shape.dims)}")
        batch, seq, _ = x.shape.dims

        q = self._split_heads(self.q_proj(x), batch, seq, self.num_heads)
        k = self._split_heads(self.k_proj(x), batch, seq, self.num_kv_heads)
        v = self._split_heads(self.v_proj(x), batch, seq, self.num_kv_heads)

        if self.num_kv_heads != self.num_heads:
            repeats = self.num_heads // self.num_kv_heads
            k = _repeat_kv(k, repeats)
            v = _repeat_kv(v, repeats)

        context = _attention(q, k, v, causal=self.causal, mask=mask)
        merged = context.transpose(1, 2).reshape(batch, seq, self.num_heads * self.head_dim)
        return self.o_proj(merged)

    def kv_cache_size(self, batch: int, seq: int, bytes_per_element: int = 4) -> int:
        """Return the bytes this layer's KV cache occupies."""
        return 2 * batch * seq * self.num_kv_heads * self.head_dim * bytes_per_element

    def __repr__(self) -> str:
        return (
            f"MultiHeadAttention(d_model={self.d_model}, num_heads={self.num_heads}, "
            f"num_kv_heads={self.num_kv_heads}, causal={self.causal})"
        )


def _repeat_kv(x: Tensor, repeats: int) -> Tensor:
    """Repeat each key/value head ``repeats`` times for grouped-query attention."""
    if repeats == 1:
        return x
    batch, heads, seq, dim = x.shape.dims
    expanded = x.reshape(batch, heads, 1, seq, dim)
    flat = Tensor.from_numpy(
        np.repeat(expanded.numpy(), repeats, axis=1).reshape(batch, heads * repeats, seq, dim), x.dtype, x.device
    )
    flat.requires_grad_(x.requires_grad)
    return flat


class FeedForward(Module):
    """The position-wise feed-forward block of a transformer layer.

    The hidden width defaults to four times the model width, which is the
    standard expansion ratio.
    """

    def __init__(self, d_model: int, d_ff: int | None = None, activation: Any = gelu, dropout: float = 0.0) -> None:
        super().__init__()
        self.fc1 = Linear(d_model, d_ff or 4 * d_model)
        self.act = Activation(activation, getattr(activation, "__name__", "activation"))
        self.fc2 = Linear(d_ff or 4 * d_model, d_model)
        self.dropout = dropout

    def forward(self, x: Tensor) -> Tensor:
        """Apply the feed-forward transform."""
        return self.fc2(self.act(self.fc1(x)))

    def __repr__(self) -> str:
        return f"FeedForward(d_model={self.fc1.in_features}, d_ff={self.fc1.out_features})"


class TransformerBlock(Module):
    """One pre-norm transformer block: attention plus feed-forward, both residual.

    Normalizing before each sublayer keeps activation magnitudes stable through
    deep stacks, which is the difference between a 12-layer and a 100-layer
    model training at all.
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int,
        d_ff: int | None = None,
        num_kv_heads: int | None = None,
        dropout: float = 0.0,
        causal: bool = True,
        norm: str = "rms",
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.causal = causal

        norm_cls = RMSNorm if norm == "rms" else LayerNorm
        norm_args = (d_model,)
        self.norm1 = norm_cls(*norm_args)
        self.attn = MultiHeadAttention(d_model, num_heads, num_kv_heads, dropout=dropout, causal=causal)
        self.norm2 = norm_cls(*norm_args)
        self.ffn = FeedForward(d_model, d_ff, dropout=dropout)

    def forward(self, x: Tensor, mask: Tensor | None = None) -> Tensor:
        """Apply attention and feed-forward sublayers with residual connections."""
        x = x + self.attn(self.norm1(x), mask=mask)
        return x + self.ffn(self.norm2(x))

    def __repr__(self) -> str:
        return f"TransformerBlock(d_model={self.d_model}, causal={self.causal})"


class PositionalEncoding(Module):
    """Fixed sinusoidal positional encodings from the original transformer paper.

    Positions beyond the table are handled by extrapolating with the analytic
    formula, so a model trained on short sequences can be evaluated on longer
    ones.
    """

    def __init__(self, d_model: int, max_length: int = 5000, dropout: float = 0.0) -> None:
        super().__init__()
        if d_model % 2:
            raise ValueError(f"d_model must be even for sinusoidal encodings, got {d_model}")
        self.d_model = d_model
        self.max_length = max_length

        positions = np.arange(max_length)[:, None]
        frequencies = np.exp(np.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        table = np.zeros((max_length, d_model), dtype=np.float32)
        table[:, 0::2] = np.sin(positions * frequencies)
        table[:, 1::2] = np.cos(positions * frequencies)
        self.register_buffer("table", Tensor.from_numpy(table), persistent=False)

    def forward(self, x: Tensor) -> Tensor:
        """Add positional encodings to a ``(batch, seq, d_model)`` input."""
        seq = x.shape.dims[1]
        if seq <= self.max_length:
            encoding = self.table.narrow(0, 0, seq)
        else:
            encoding = self._extrapolate(seq)
        return x + encoding

    def _extrapolate(self, seq: int) -> Tensor:
        """Generate encodings beyond the precomputed table."""
        positions = np.arange(seq)[:, None]
        frequencies = np.exp(np.arange(0, self.d_model, 2) * (-math.log(10000.0) / self.d_model))
        table = np.zeros((seq, self.d_model), dtype=np.float32)
        table[:, 0::2] = np.sin(positions * frequencies)
        table[:, 1::2] = np.cos(positions * frequencies)
        return Tensor.from_numpy(table)


class TransformerEncoder(Module):
    """A stack of :class:`TransformerBlock` layers with a final normalization.

    Args:
        vocab_size: vocabulary size, or 0 when a separate embedding is supplied.
        d_model: model width.
        num_layers: number of blocks.
        num_heads: query head count.
        d_ff: feed-forward width; defaults to ``4 * d_model``.
        num_kv_heads: key/value head count for grouped-query attention.
        max_length: positional table length.
        norm: ``"rms"`` or ``"layernorm"``.
    """

    def __init__(
        self,
        vocab_size: int,
        d_model: int,
        num_layers: int,
        num_heads: int,
        d_ff: int | None = None,
        num_kv_heads: int | None = None,
        max_length: int = 512,
        dropout: float = 0.0,
        causal: bool = True,
        norm: str = "rms",
    ) -> None:
        super().__init__()
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.num_layers = num_layers

        if vocab_size:
            self.embedding = _Embedding(vocab_size, d_model)
        else:
            self.embedding = None
        self.position = PositionalEncoding(d_model, max_length)
        self.blocks = _BlockList(
            [
                TransformerBlock(d_model, num_heads, d_ff, num_kv_heads, dropout, causal, norm)
                for _ in range(num_layers)
            ]
        )
        norm_cls = RMSNorm if norm == "rms" else LayerNorm
        self.final_norm = norm_cls(d_model)

    def forward(self, tokens: Tensor, mask: Tensor | None = None) -> Tensor:
        """Embed ``tokens`` and run them through every block."""
        if self.embedding is None:
            raise RuntimeError("This encoder has no embedding; pass pre-embedded inputs or set vocab_size")
        x = self.position(self.embedding(tokens))
        for block in self.blocks:
            x = block(x, mask=mask)
        return self.final_norm(x)

    def parameter_groups(self) -> dict[str, int]:
        """Return the parameter count split by role, useful for LR tuning."""
        embedding = self.embedding.num_parameters() if self.embedding is not None else 0
        return {
            "embedding": embedding,
            "transformer": sum(b.num_parameters() for b in self.blocks),
            "total": self.num_parameters(),
        }


class _Embedding(Module):
    """Thin wrapper so the encoder does not depend on the linear module's API."""

    def __init__(self, num_embeddings: int, embedding_dim: int) -> None:
        super().__init__()
        from astrovox.nn.linear import Embedding

        self.table = Embedding(num_embeddings, embedding_dim)

    def forward(self, indices: Tensor) -> Tensor:
        """Look up embeddings for ``indices``."""
        return self.table(indices)

    @property
    def weight(self) -> Tensor:
        """The underlying embedding table."""
        return self.table.weight

    def num_parameters(self, trainable_only: bool = True) -> int:
        """Count the table entries."""
        return self.table.weight.numel


class _BlockList(Module):
    """Ordered container of transformer blocks."""

    def __init__(self, blocks: Sequence[Module]) -> None:
        super().__init__()
        self.blocks = list(blocks)
        for i, block in enumerate(self.blocks):
            self._modules[str(i)] = block

    def __len__(self) -> int:
        return len(self.blocks)

    def __iter__(self):
        return iter(self.blocks)

    def __getitem__(self, index: int) -> Module:
        return self.blocks[index]

    def num_parameters(self, trainable_only: bool = True) -> int:
        """Total parameters across every block."""
        return sum(b.num_parameters(trainable_only) for b in self.blocks)
