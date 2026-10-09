import numpy as np
import pytest
from ..mixture_of_experts import MoELayer


class TestMoELayer:
    def test_output_shape(self):
        B, T, C = 2, 10, 64
        model = MoELayer(d_model=C, num_experts=4)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert out.shape == (B, T, C)

    def test_top_k_routing(self):
        B, T, C = 2, 5, 32
        model = MoELayer(d_model=C, num_experts=4, top_k=2)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert out.shape == (B, T, C)

    def test_load_balancing_loss(self):
        B, T, C = 2, 5, 32
        model = MoELayer(d_model=C, num_experts=4)
        x = np.random.randn(B, T, C)
        loss = model.load_balancing_loss(x)
        assert np.isfinite(loss)

    def test_invalid_top_k(self):
        with pytest.raises(AssertionError):
            MoELayer(d_model=32, num_experts=4, top_k=5)
