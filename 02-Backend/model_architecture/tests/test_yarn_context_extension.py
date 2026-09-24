import numpy as np
import pytest
from ..yarn_context_extension import YaRNContextExtension


class TestYaRNContextExtension:
    def test_output_shape(self):
        B, T, C = 2, 10, 64
        model = YaRNContextExtension(d_model=C, num_heads=4, original_max_seq_len=128, extended_max_seq_len=256)
        q = np.random.randn(B, T, 4, C // 4)
        k = np.random.randn(B, T, 4, C // 4)
        q_out, k_out = model.apply(q, k)
        assert q_out.shape == (B, T, 4, C // 4)
        assert k_out.shape == (B, T, 4, C // 4)

    def test_temperature_scaling(self):
        B, T, C = 2, 5, 32
        model = YaRNContextExtension(d_model=C, num_heads=4, original_max_seq_len=64, extended_max_seq_len=128)
        q = np.random.randn(B, T, 4, C // 4)
        k = np.random.randn(B, T, 4, C // 4)
        model.temperature = 1.1
        q_out, k_out = model.apply(q, k)
        assert not np.allclose(q_out, q)
