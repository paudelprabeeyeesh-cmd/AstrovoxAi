"""Tests for chunked attention and its memory accounting."""

import math

import numpy as np
import pytest

from astrovox import tensor
from astrovox.nn.transformer import _attention
from astrovox.ops.attention import (
    chunked_attention,
    chunked_score_bytes,
    memory_saving_factor,
    score_matrix_bytes,
)


def reference_attention(q, k, v, causal=True):
    """Dense attention, used as the reference the chunked path must match."""
    return _attention(tensor(q), tensor(k), tensor(v), causal=causal).numpy()


@pytest.mark.parametrize("chunk_size", [1, 2, 3, 4, 8, 16])
def test_chunked_matches_dense_causal(chunk_size):
    rng = np.random.default_rng(0)
    batch, heads, seq_len, dim = 2, 2, 8, 4
    q = rng.standard_normal((batch, heads, seq_len, dim)).astype(np.float32)
    k = rng.standard_normal((batch, heads, seq_len, dim)).astype(np.float32)
    v = rng.standard_normal((batch, heads, seq_len, dim)).astype(np.float32)

    got = chunked_attention(tensor(q), tensor(k), tensor(v), causal=True, chunk_size=chunk_size).numpy()
    expected = reference_attention(q, k, v, causal=True)
    assert np.allclose(got, expected, atol=1e-5), np.abs(got - expected).max()


@pytest.mark.parametrize("chunk_size", [1, 3, 8, 64])
def test_chunked_matches_dense_non_causal(chunk_size):
    rng = np.random.default_rng(1)
    batch, heads, seq_len, dim = 1, 3, 8, 4
    q = rng.standard_normal((batch, heads, seq_len, dim)).astype(np.float32)
    k = rng.standard_normal((batch, heads, seq_len, dim)).astype(np.float32)
    v = rng.standard_normal((batch, heads, seq_len, dim)).astype(np.float32)

    got = chunked_attention(tensor(q), tensor(k), tensor(v), causal=False, chunk_size=chunk_size).numpy()
    expected = reference_attention(q, k, v, causal=False)
    assert np.allclose(got, expected, atol=1e-5), np.abs(got - expected).max()


def test_chunked_handles_a_partial_final_chunk():
    """A sequence that is not a multiple of the chunk size must still be exact."""
    rng = np.random.default_rng(2)
    q, k, v = (rng.standard_normal((1, 1, 7, 4)).astype(np.float32) for _ in range(3))
    got = chunked_attention(tensor(q), tensor(k), tensor(v), causal=True, chunk_size=3).numpy()
    assert np.allclose(got, reference_attention(q, k, v, True), atol=1e-5)


def test_causal_chunked_ignores_future_tokens():
    """Changing a later token must not change any earlier output."""
    rng = np.random.default_rng(3)
    q, k, v = (rng.standard_normal((1, 1, 6, 4)).astype(np.float32) for _ in range(3))
    first = chunked_attention(tensor(q), tensor(k), tensor(v), causal=True, chunk_size=2).numpy()

    k2, v2 = k.copy(), v.copy()
    k2[:, :, 4:] += 100.0
    v2[:, :, 4:] += 100.0
    second = chunked_attention(tensor(q), tensor(k2), tensor(v2), causal=True, chunk_size=2).numpy()

    assert np.allclose(first[:, :, :4], second[:, :, :4], atol=1e-6)


def test_attention_rows_sum_to_one_over_values():
    """Each output must be a convex combination of the value vectors."""
    rng = np.random.default_rng(4)
    q, k, v = (rng.standard_normal((1, 1, 5, 3)).astype(np.float32) for _ in range(3))
    out = chunked_attention(tensor(q), tensor(k), tensor(v), causal=True, chunk_size=2).numpy()
    # A convex combination stays within the range of the values it averages.
    for i in range(out.shape[2]):
        assert out[0, 0, i].min() >= v[0, 0].min() - 1e-4
        assert out[0, 0, i].max() <= v[0, 0].max() + 1e-4


def test_rejects_a_bad_chunk_size():
    q = np.zeros((1, 1, 4, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="chunk_size"):
        chunked_attention(tensor(q), tensor(q), tensor(q), chunk_size=0)


def test_rejects_wrong_rank():
    q = np.zeros((4, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="4-D"):
        chunked_attention(tensor(q), tensor(q), tensor(q))


def test_rejects_mismatched_head_dim():
    q = np.zeros((1, 1, 4, 4), dtype=np.float32)
    k = np.zeros((1, 1, 4, 8), dtype=np.float32)
    with pytest.raises(ValueError, match="head dimensions"):
        chunked_attention(tensor(q), tensor(k), tensor(k))


def test_rejects_mismatched_batch():
    q = np.zeros((1, 1, 4, 4), dtype=np.float32)
    k = np.zeros((2, 1, 4, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="batch"):
        chunked_attention(tensor(q), tensor(k), tensor(k))


def test_backward_is_refused_rather_than_wrong():
    """Training through this path would need the dense gradient; say so plainly."""
    q = np.random.default_rng(5).standard_normal((1, 1, 4, 4)).astype(np.float32)
    t = tensor(q).requires_grad_(True)
    with pytest.raises(NotImplementedError, match="forward-only"):
        chunked_attention(t, tensor(q), tensor(q), chunk_size=2).sum().backward()


def test_the_engine_does_not_silently_skip_a_forward_only_path():
    """A missing backward must be loud, or it looks like a layer that cannot learn."""
    from astrovox.ops.attention import OnlineSoftmaxAttention

    assert OnlineSoftmaxAttention.supports_backward is False


class TestMemoryAccounting:
    def test_dense_grows_quadratically(self):
        assert score_matrix_bytes(1, 1, 16) == 16 * 16 * 4
        assert score_matrix_bytes(1, 1, 1024) > 1_000_000

    def test_chunked_is_bounded_by_the_chunk(self):
        dense = score_matrix_bytes(1, 8, 2048)
        chunked = chunked_score_bytes(1, 8, 2048, chunk_size=128)
        assert chunked < dense / 100

    def test_saving_grows_with_sequence_length(self):
        short = memory_saving_factor(128, 32)
        long = memory_saving_factor(4096, 32)
        assert long > short

    def test_saving_is_at_least_one(self):
        assert memory_saving_factor(64, 64) >= 1.0

    def test_real_saving_for_a_long_sequence(self):
        """A 4096-token sequence with 128-token chunks should save a lot."""
        factor = memory_saving_factor(4096, 128, causal=True)
        assert factor > 10, factor
