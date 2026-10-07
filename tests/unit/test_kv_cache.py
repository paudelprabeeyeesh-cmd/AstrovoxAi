"""Tests for KV cache and streaming inference utilities."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.kv_cache import ChunkedPrefill, KVCache, alibi, rope
from astrovox.tensor.tensor import Tensor


def test_kv_cache_update_and_get():
    cache = KVCache()
    key = Tensor.from_numpy(np.ones((1, 2, 4), dtype=np.float32))
    value = Tensor.from_numpy(np.ones((1, 2, 4), dtype=np.float32))
    cache.update(0, key, value)
    entry = cache.get(0)
    assert entry is not None
    assert entry.key.shape.dims == (1, 2, 4)


def test_kv_cache_reuse_appends():
    cache = KVCache()
    key1 = Tensor.from_numpy(np.ones((1, 2, 4), dtype=np.float32))
    value1 = Tensor.from_numpy(np.ones((1, 2, 4), dtype=np.float32))
    key2 = Tensor.from_numpy(np.ones((1, 1, 4), dtype=np.float32))
    value2 = Tensor.from_numpy(np.ones((1, 1, 4), dtype=np.float32))
    cache.update(0, key1, value1)
    cache.update(0, key2, value2)
    entry = cache.get(0)
    assert entry.key.shape.dims[1] == 3


def test_chunked_prefill_splits_sequence():
    splitter = ChunkedPrefill(chunk_size=2)
    x = Tensor.from_numpy(np.ones((1, 5, 4), dtype=np.float32))
    chunks = splitter.split(x)
    assert len(chunks) == 3


def test_rope_preserves_shape():
    x = Tensor.from_numpy(np.ones((1, 4, 8), dtype=np.float32))
    result = rope(x, dim=-2)
    assert result.shape.dims == (1, 4, 8)


def test_alibi_returns_tensor():
    x = Tensor.from_numpy(np.ones((2, 4, 4), dtype=np.float32))
    result = alibi(x, num_heads=2)
    assert result.shape.dims == (2, 4, 4)
