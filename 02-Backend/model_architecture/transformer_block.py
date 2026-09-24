import numpy as np
from .rmsnorm import RMSNorm


class MultiHeadAttention:
    def __init__(self, d_model, num_heads):
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        assert d_model % num_heads == 0

        self.W_q = np.random.randn(d_model, d_model) * 0.02
        self.W_k = np.random.randn(d_model, d_model) * 0.02
        self.W_v = np.random.randn(d_model, d_model) * 0.02
        self.W_o = np.random.randn(d_model, d_model) * 0.02
        self.scale = self.head_dim ** -0.5

    def forward(self, x, mask=None):
        B, T, C = x.shape
        q = x @ self.W_q
        k = x @ self.W_k
        v = x @ self.W_v

        q = q.reshape(B, T, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
        k = k.reshape(B, T, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
        v = v.reshape(B, T, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)

        attn = (q @ k.transpose(0, 1, 3, 2)) * self.scale
        if mask is not None:
            attn = np.where(mask == 0, -1e9, attn)
        attn = np.exp(attn - np.max(attn, axis=-1, keepdims=True))
        attn = attn / np.sum(attn, axis=-1, keepdims=True)

        out = attn @ v
        out = out.transpose(0, 2, 1, 3).reshape(B, T, C)
        out = out @ self.W_o
        return out


class FeedForward:
    def __init__(self, d_model, d_ff=None):
        if d_ff is None:
            d_ff = d_model * 4
        self.W1 = np.random.randn(d_model, d_ff) * 0.02
        self.W2 = np.random.randn(d_ff, d_model) * 0.02
        self.b1 = np.zeros(d_ff)
        self.b2 = np.zeros(d_model)

    def forward(self, x):
        x = np.maximum(0, x @ self.W1 + self.b1)
        return x @ self.W2 + self.b2


class TransformerBlock:
    def __init__(self, d_model, num_heads, d_ff=None):
        self.attention = MultiHeadAttention(d_model, num_heads)
        self.ffn = FeedForward(d_model, d_ff)
        self.ln1 = RMSNorm(d_model)
        self.ln2 = RMSNorm(d_model)

    def forward(self, x, mask=None):
        x = x + self.attention.forward(self.ln1.forward(x), mask)
        x = x + self.ffn.forward(self.ln2.forward(x))
        return x
