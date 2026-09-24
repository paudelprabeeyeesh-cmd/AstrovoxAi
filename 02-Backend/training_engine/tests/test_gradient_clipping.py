import numpy as np
import pytest
from training_engine.gradient_clipping import clip_grad_norm


def test_no_clip_when_under_threshold():
    p = np.ones((4, 4), dtype=np.float32)
    g = np.ones((4, 4), dtype=np.float32) * 0.1
    out, total_norm = clip_grad_norm([(p, g)], max_norm=1.0)
    assert total_norm < 1.0
    assert np.allclose(out[0][1], g)


def test_clip_when_over_threshold():
    p = np.ones((4, 4), dtype=np.float32)
    g = np.ones((4, 4), dtype=np.float32) * 1e3
    out, total_norm = clip_grad_norm([(p, g)], max_norm=1.0)
    assert total_norm > 1.0
    clipped = out[0][1]
    clipped_norm = np.sqrt(np.sum(clipped ** 2))
    assert np.isclose(clipped_norm, 1.0, atol=1e-5)


def test_multiple_params():
    p1 = np.ones((2, 2), dtype=np.float32)
    g1 = np.ones((2, 2), dtype=np.float32) * 1e3
    p2 = np.ones((2, 2), dtype=np.float32)
    g2 = np.ones((2, 2), dtype=np.float32) * 1e3
    out, total_norm = clip_grad_norm([(p1, g1), (p2, g2)], max_norm=1.0)
    assert len(out) == 2
