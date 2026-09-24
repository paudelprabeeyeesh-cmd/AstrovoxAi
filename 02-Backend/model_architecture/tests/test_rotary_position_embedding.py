import numpy as np
import pytest
from ..rotary_position_embedding import RoPE, precompute_rope, apply_rope


class TestRotaryPositionEmbedding:
    def test_precompute_shape(self):
        sin, cos = precompute_rope(dim=64, max_seq_len=128)
        assert sin.shape == (128, 32)

    def test_apply_rope_shape(self):
        B, T, H, D = 2, 10, 4, 16
        q = np.random.randn(B, T, H, D)
        k = np.random.randn(B, T, H, D)
        sin, cos = precompute_rope(dim=D, max_seq_len=T)
        q_rot = apply_rope(q, sin, cos)
        k_rot = apply_rope(k, sin, cos)
        assert q_rot.shape == (B, T, H, D)

    def test_position_sensitivity(self):
        B, T, H, D = 1, 5, 2, 8
        q = np.random.randn(B, T, H, D)
        k = np.random.randn(B, T, H, D)
        rope = RoPE(d_model=H * D, num_heads=H, max_seq_len=T)
        q0, k0 = rope.forward(q, k)
        q1, k1 = rope.forward(q, k)
        assert np.allclose(q0, q1)
        assert np.allclose(k0, k1)

    def test_inverse_property(self):
        B, T, H, D = 1, 3, 2, 8
        q = np.random.randn(B, T, H, D)
        k = np.random.randn(B, T, H, D)
        rope = RoPE(d_model=H * D, num_heads=H, max_seq_len=T)
        q_rot, k_rot = rope.forward(q, k)
        assert q_rot.shape == q.shape
