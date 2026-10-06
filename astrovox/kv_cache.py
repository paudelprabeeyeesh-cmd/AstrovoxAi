"""KV cache and streaming inference utilities.

These helpers make autoregressive decoding cheaper by reusing previously
computed key/value states. They are intentionally separate from the core
transformer module so they can be reviewed and tested independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from astrovox.tensor.tensor import Tensor


@dataclass
class KVCacheEntry:
    key: Tensor
    value: Tensor


class KVCache:
    """Per-layer KV cache for autoregressive decoding."""

    def __init__(self) -> None:
        self.layers: dict[int, KVCacheEntry] = {}

    def update(self, layer: int, key: Tensor, value: Tensor) -> Tuple[Tensor, Tensor]:
        entry = self.layers.get(layer)
        if entry is None:
            self.layers[layer] = KVCacheEntry(key=key, value=value)
            return key, value
        new_key = np.concatenate([entry.key.numpy(), key.numpy()], axis=-2)
        new_value = np.concatenate([entry.value.numpy(), value.numpy()], axis=-2)
        entry.key = Tensor.from_numpy(new_key, key.dtype, key.device)
        entry.value = Tensor.from_numpy(new_value, value.dtype, value.device)
        return entry.key, entry.value

    def get(self, layer: int) -> Optional[KVCacheEntry]:
        return self.layers.get(layer)

    def reset(self) -> None:
        self.layers.clear()


class ChunkedPrefill:
    """Process long prompts in chunks to bound peak memory."""

    def __init__(self, chunk_size: int = 2048) -> None:
        self.chunk_size = max(1, chunk_size)

    def split(self, x: Tensor) -> Tuple[Tensor, ...]:
        seq = x.shape.dims[-2]
        chunks = []
        for start in range(0, seq, self.chunk_size):
            end = min(start + self.chunk_size, seq)
            slices = [slice(None)] * (x.ndim - 1) + [slice(start, end)]
            chunks.append(x[tuple(slices)])
        return tuple(chunks)


def rope(x: Tensor, dim: int = -1, base: float = 10000.0) -> Tensor:
    """Rotary positional embedding (RoPE)."""
    array = x.numpy().astype(np.float64)
    shape = array.shape
    if dim < 0:
        dim = len(shape) + dim
    length = shape[dim]
    positions = np.arange(length, dtype=np.float64)
    freqs = 1.0 / (base ** (np.arange(0, array.shape[-1], 2, dtype=np.float64) / array.shape[-1]))
    sinusoids = np.einsum("i,j->ij", positions, freqs)
    sin = np.sin(sinusoids)
    cos = np.cos(sinusoids)
    out = np.empty_like(array)
    out[..., ::2] = array[..., ::2] * cos - array[..., 1::2] * sin
    out[..., 1::2] = array[..., ::2] * sin + array[..., 1::2] * cos
    return Tensor.from_numpy(out.astype(x.dtype.np_dtype), x.dtype, x.device)


def alibi(x: Tensor, num_heads: int) -> Tensor:
    """Attention with linear biases (ALiBi)."""
    array = x.numpy()
    seq = array.shape[-2]
    slopes = np.power(2.0, -8.0 * np.arange(1, num_heads + 1) / num_heads)
    bias = np.tile(slopes[:, None, None] * np.arange(seq)[None, None, :], (1, seq, 1))
    bias = np.triu(bias, 1)
    return Tensor.from_numpy((array - bias).astype(x.dtype.np_dtype), x.dtype, x.device)
