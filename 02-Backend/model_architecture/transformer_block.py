import numpy as np
from .rmsnorm import RMSNorm
from .attention import MultiHeadAttention
from .feedforward import FeedForward


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
