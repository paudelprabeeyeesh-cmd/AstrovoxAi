import numpy as np
from ..swiglu_activation import SwiGLUActivation


class TestSwiGLUActivation:
    def test_output_shape(self):
        B, T, C = 2, 10, 64
        model = SwiGLUActivation(d_model=C)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert out.shape == (B, T, C)

    def test_swish_positive(self):
        model = SwiGLUActivation(d_model=32)
        np.array([[1.0]])
        s = model.swish(1.0)
        assert s > 0

    def test_swish_negative(self):
        model = SwiGLUActivation(d_model=32)
        np.array([[-1.0]])
        s = model.swish(-1.0)
        assert -1.0 < s < 0.0
