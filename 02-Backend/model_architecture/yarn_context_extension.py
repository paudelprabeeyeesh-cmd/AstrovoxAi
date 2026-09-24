import numpy as np
from .rotary_position_embedding import RoPE


class YaRNContextExtension:
    def __init__(self, d_model, num_heads, original_max_seq_len, extended_max_seq_len,
                 alpha=1.0, beta=1.0, base=10000.0):
        self.alpha = alpha
        self.beta = beta
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads

        self.scale = (extended_max_seq_len / original_max_seq_len) ** (1.0 / self.alpha)
        scaled_dim = self.head_dim / self.scale

        theta = base ** (-np.arange(0, self.head_dim, 2) / self.scale)
        positions = np.arange(extended_max_seq_len)
        freqs = np.outer(positions, theta)
        sin = np.sin(freqs)
        cos = np.cos(freqs)
        self.sin = sin
        self.cos = cos
        self.temperature = 1.0

    def apply(self, q, k):
        B, T, _, _ = q.shape
        sin_exp = self.sin[:T][None, :, None, :]
        cos_exp = self.cos[:T][None, :, None, :]

        q1 = q[..., ::2]
        q2 = q[..., 1::2]
        q_rot = np.stack([
            q1 * cos_exp - q2 * sin_exp,
            q1 * sin_exp + q2 * cos_exp
        ], axis=-1).reshape(B, T, self.num_heads, self.head_dim)

        k1 = k[..., ::2]
        k2 = k[..., 1::2]
        k_rot = np.stack([
            k1 * cos_exp - k2 * sin_exp,
            k1 * sin_exp + k2 * cos_exp
        ], axis=-1).reshape(B, T, self.num_heads, self.head_dim)

        q = (q - q_rot) * self.temperature + q_rot
        k = (k - k_rot) * self.temperature + k_rot
        return q, k
