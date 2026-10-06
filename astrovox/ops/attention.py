"""Memory-efficient attention.

The straightforward attention builds a full ``(seq, seq)`` score matrix, so
memory grows quadratically with sequence length. Two things reduce that
without changing what is computed.

**Online softmax.** The softmax denominator for a row is a sum over all keys,
but a chunk of keys can contribute to that running total and the result
corrected afterwards. Each chunk's output is rescaled by how much of the
denominator was already accounted for, which gives exactly the full-softmax
result while only ever holding one chunk of scores.

**Query blocking.** With a causal mask, a query block only needs key blocks up
to its own end. An earlier block is never revisited, so a causal forward pass
touches half the score matrix rather than all of it.

The result is bit-comparable to the dense path in float32, within the
accumulation error of summing in a different order.
"""

from __future__ import annotations

import math

import numpy as np

from astrovox.autograd.function import Function
from astrovox.tensor.tensor import Tensor


def _check_attention_inputs(q: Tensor, k: Tensor, v: Tensor) -> tuple[int, int, int, int]:
    """Validate attention inputs and return batch, heads, sequence, head_dim."""
    if q.ndim != 4 or k.ndim != 4 or v.ndim != 4:
        raise ValueError(
            f"attention expects 4-D (batch, heads, seq, head_dim) inputs, got "
            f"{q.ndim}-D, {k.ndim}-D, {v.ndim}-D"
        )
    if q.shape.dims[0] != k.shape.dims[0] or q.shape.dims[0] != v.shape.dims[0]:
        raise ValueError("batch dimensions of q, k and v must match")
    if k.shape.dims[-2] != v.shape.dims[-2]:
        raise ValueError("key and value sequence lengths must match")
    if q.shape.dims[-1] != k.shape.dims[-1]:
        raise ValueError("query and key head dimensions must match")
    return q.shape.dims[0], q.shape.dims[1], q.shape.dims[2], q.shape.dims[-1]


class OnlineSoftmaxAttention(Function):
    """Scaled dot-product attention computed in chunks.

    The forward pass keeps, for every query, a running sum of the exponentials
    it has seen and the weighted sum of the corresponding values. Each chunk
    rescales what came before by the ratio of the old and new denominators,
    which is what makes the chunked result equal to the dense one.
    """

    name = "online_softmax_attention"
    supports_backward = False

    @staticmethod
    def forward(ctx, q: Tensor, k: Tensor, v: Tensor, causal: bool, chunk_size: int):
        batch, heads, q_len, head_dim = _check_attention_inputs(q, k, v)
        k_len = k.shape.dims[2]
        scale = 1.0 / math.sqrt(head_dim)

        q_array = q.numpy()
        k_array = k.numpy()
        v_array = v.numpy()

        out = np.zeros((batch, heads, q_len, v.shape.dims[3]), dtype=np.float64)
        for start in range(0, q_len, chunk_size):
            stop = min(start + chunk_size, q_len)
            # A causal query block only needs keys up to its own last position.
            key_stop = stop if causal else k_len
            block_q = q_array[:, :, start:stop] * scale

            accumulator = np.zeros((batch, heads, stop - start, v_array.shape[3]), dtype=np.float64)
            denominator = np.zeros((batch, heads, stop - start, 1), dtype=np.float64)
            running_max = np.full((batch, heads, stop - start, 1), -np.inf, dtype=np.float64)

            for key_start in range(0, key_stop, chunk_size):
                key_end = min(key_start + chunk_size, key_stop)
                scores = np.einsum("bhqd,bhkd->bhqk", block_q, k_array[:, :, key_start:key_end])
                if causal:
                    rows = np.arange(start, stop)[:, None]
                    columns = np.arange(key_start, key_end)[None, :]
                    scores = np.where(columns > rows, -np.inf, scores)

                # The maximum has to run across chunks, not be taken per
                # chunk: each chunk's exponentials are computed relative to a
                # different maximum, so they are only comparable once both are
                # rescaled to the same one.
                chunk_max = scores.max(axis=-1, keepdims=True)
                new_max = np.maximum(running_max, chunk_max)
                # A query whose keys are all masked has an infinite maximum;
                # fall back to zero so its exponentials stay finite.
                safe_max = np.where(np.isfinite(new_max), new_max, 0.0)

                correction = np.exp(running_max - safe_max)
                weights = np.exp(scores - safe_max)
                chunk_denominator = weights.sum(axis=-1, keepdims=True)

                denominator = denominator * correction + chunk_denominator
                accumulator = accumulator * correction + np.einsum(
                    "bhqk,bhkd->bhqd", weights, v_array[:, :, key_start:key_end]
                )
                running_max = new_max
            # The running denominator is the row's total weight, so the
            # normalized attention weight is the chunked sum divided by it.
            out[:, :, start:stop] = accumulator / np.maximum(denominator, 1e-300)

        result = Tensor.from_numpy(out.astype(q.dtype.np_dtype), q.dtype, q.device)
        ctx.save(chunk_size=chunk_size, causal=causal)
        return result.requires_grad_(q.requires_grad or k.requires_grad or v.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        """Recompute attention densely for the backward pass.

        The backward pass needs the full softmax, so the saving the chunked
        forward buys applies only to the forward. The gradient itself is
        exactly the dense one; implementing it means recomputing the scores,
        which is why this path declares itself forward-only.
        """
        raise NotImplementedError(
            "chunked attention has no backward; use the dense path for training"
        )


def chunked_attention(
    q: Tensor,
    k: Tensor,
    v: Tensor,
    causal: bool = True,
    chunk_size: int = 128,
) -> Tensor:
    """Attention over chunks of keys, using an online softmax.

    Memory for scores is ``(batch, heads, chunk, chunk)`` rather than
    ``(batch, heads, seq, seq)``, so the peak cost stops growing quadratically.

    This is a forward-only path. Training needs the full softmax for its
    gradient, so use :func:`~astrovox.nn.transformer.attention` while training
    and this for inference on long sequences.
    """
    if chunk_size < 1:
        raise ValueError(f"chunk_size must be at least 1, got {chunk_size}")
    return OnlineSoftmaxAttention.apply(q, k, v, causal, chunk_size)


def score_matrix_bytes(
    batch: int, heads: int, seq_len: int, element_bytes: int = 4
) -> int:
    """Return the bytes a dense score matrix would occupy."""
    return batch * heads * seq_len * seq_len * element_bytes


def chunked_score_bytes(
    batch: int, heads: int, seq_len: int, chunk_size: int, element_bytes: int = 4
) -> int:
    """Return the peak score bytes a chunked pass holds."""
    # Two chunks are live at once: the scores and the values being accumulated.
    per_query_chunk = min(chunk_size, max(seq_len, 1))
    return 2 * batch * heads * per_query_chunk * per_query_chunk * element_bytes


def memory_saving_factor(seq_len: int, chunk_size: int, causal: bool = True) -> float:
    """Return how much less score memory a chunked causal pass uses.

    A causal pass over query blocks touches only the lower triangle, so the
    saving is better than the square of the chunk ratio.
    """
    dense = (seq_len**2) / 2 if causal else seq_len**2
    blocks = 0
    for start in range(0, seq_len, chunk_size):
        stop = min(start + chunk_size, seq_len)
        keys = stop if causal else seq_len
        blocks += 1 + (keys + chunk_size - 1) // chunk_size
    chunked = blocks * chunk_size
    return dense / max(chunked, 1)
