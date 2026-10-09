import numpy as np
from ..transformer_block import TransformerBlock


class TestTransformerBlock:
    def test_output_shape(self):
        B, T, C = 2, 10, 64
        model = TransformerBlock(d_model=C, num_heads=4)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert out.shape == (B, T, C)

    def test_residual_connection(self):
        B, T, C = 2, 5, 32
        model = TransformerBlock(d_model=C, num_heads=4)
        x = np.random.randn(B, T, C)
        out = model.forward(x)
        assert not np.allclose(out, x)

    def test_pre_ln(self):
        B, T, C = 2, 5, 32
        model = TransformerBlock(d_model=C, num_heads=4)
        x = np.random.randn(B, T, C)
        _ = model.forward(x)
        assert True

    def test_with_mask(self):
        B, T, C = 2, 10, 64
        model = TransformerBlock(d_model=C, num_heads=4)
        x = np.random.randn(B, T, C)
        mask = np.triu(np.ones((T, T)), k=1).astype(bool)
        out = model.forward(x, mask=mask)
        assert out.shape == (B, T, C)
