import numpy as np
import pytest
from ..rmsnorm import RMSNorm


class TestRMSNorm:
    def test_output_shape(self):
        B, T, C = 2, 10, 64
        model = RMSNorm(d_model=C)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert out.shape == (B, T, C)

    def test_zero_input(self):
        C = 32
        model = RMSNorm(d_model=C)
        x = np.zeros((2, 5, C))
        out = model.forward(x)
        assert not np.any(np.isnan(out))

    def test_numerical_stability(self):
        C = 32
        model = RMSNorm(d_model=C)
        x = np.random.randn(2, 5, C) * 1e6
        out = model.forward(x)
        assert np.all(np.isfinite(out))
