import numpy as np
import pytest
from ..grouped_query_attention import GroupedQueryAttention


class TestGroupedQueryAttention:
    def test_output_shape(self):
        B, T, C = 2, 10, 64
        model = GroupedQueryAttention(d_model=C, num_q_heads=8, num_kv_heads=2)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert out.shape == (B, T, C)

    def test_kv_reshape(self):
        B, T, C = 2, 5, 32
        model = GroupedQueryAttention(d_model=C, num_q_heads=8, num_kv_heads=2)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert out.shape == (B, T, C)

    def test_invalid_heads(self):
        with pytest.raises(AssertionError):
            GroupedQueryAttention(d_model=32, num_q_heads=7, num_kv_heads=2)
