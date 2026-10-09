import numpy as np


def precompute_rope(dim, max_seq_len, base=10000.0):
    theta = base ** (-np.arange(0, dim, 2) / dim)
    positions = np.arange(max_seq_len)
    freqs = np.outer(positions, theta)
    sin = np.sin(freqs)
    cos = np.cos(freqs)
    return sin, cos


def apply_rope(x, sin, cos):
    B, T, num_heads, head_dim = x.shape
    x1 = x[..., ::2]
    x2 = x[..., 1::2]
    sin_exp = sin[:T][None, :, None, :]
    cos_exp = cos[:T][None, :, None, :]
    rotated = np.stack([
        x1 * cos_exp - x2 * sin_exp,
        x1 * sin_exp + x2 * cos_exp
    ], axis=-1).reshape(B, T, num_heads, head_dim)
    return rotated


class RoPE:
    def __init__(self, d_model, num_heads, max_seq_len=2048, base=10000.0):
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        sin, cos = precompute_rope(self.head_dim, max_seq_len, base)
        self.sin = sin
        self.cos = cos

    def forward(self, q, k):
        q_rotated = apply_rope(q, self.sin, self.cos)
        k_rotated = apply_rope(k, self.sin, self.cos)
        return q_rotated, k_rotated
