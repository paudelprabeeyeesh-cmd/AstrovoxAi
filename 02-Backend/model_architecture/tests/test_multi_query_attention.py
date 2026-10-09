import numpy as np
from ..multi_query_attention import MultiQueryAttention


class TestMultiQueryAttention:
    def test_output_shape(self):
        B, T, C = 2, 10, 64
        model = MultiQueryAttention(d_model=C, num_heads=8)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert out.shape == (B, T, C)

    def test_single_kv_head(self):
        B, T, C = 2, 5, 32
        model = MultiQueryAttention(d_model=C, num_heads=4)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert out.shape == (B, T, C)
