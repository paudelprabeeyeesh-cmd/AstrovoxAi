import numpy as np


class MultiQueryAttention:
    def __init__(self, d_model, num_heads):
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads

        self.W_q = np.random.randn(d_model, d_model) * 0.02
        self.W_k = np.random.randn(d_model, self.head_dim) * 0.02
        self.W_v = np.random.randn(d_model, self.head_dim) * 0.02
        self.W_o = np.random.randn(d_model, d_model) * 0.02
        self.scale = self.head_dim ** -0.5

    def forward(self, x, mask=None):
        B, T, C = x.shape
        q = x @ self.W_q
        k = x @ self.W_k
        v = x @ self.W_v

        q = q.reshape(B, T, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
        k = k.reshape(B, T, 1, self.head_dim).transpose(0, 2, 1, 3)
        v = v.reshape(B, T, 1, self.head_dim).transpose(0, 2, 1, 3)

        k = np.repeat(k, self.num_heads, axis=1)
        v = np.repeat(v, self.num_heads, axis=1)

        attn = (q @ k.transpose(0, 1, 3, 2)) * self.scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, -1e9)
        attn = np.exp(attn - np.max(attn, axis=-1, keepdims=True))
        attn = attn / np.sum(attn, axis=-1, keepdims=True)

        out = attn @ v
        out = out.transpose(0, 2, 1, 3).reshape(B, T, C)
        out = out @ self.W_o
        return out
