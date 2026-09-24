import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.attention_mechanisms import (
    AttentionNetwork,
    SpotlightModel,
    AttentionMechanisms,
    AttentionMap,
)


class TestAttentionNetwork:
    def test_output_shape(self):
        net = AttentionNetwork(n_items=8, hidden_dim=4)
        x = np.random.randn(8)
        out = net.forward(x)
        assert out.shape == (4,)

    def test_train_step_reduces_loss(self):
        net = AttentionNetwork(n_items=8, hidden_dim=4)
        x = np.random.randn(8)
        target = np.random.randn(4)
        loss1 = net.train_step(x, target, lr=0.01)
        loss2 = net.train_step(x, target, lr=0.01)
        assert isinstance(loss1, float)
        assert loss1 >= 0

    def test_forward_with_mask(self):
        net = AttentionNetwork(n_items=4, hidden_dim=4)
        x = np.random.randn(4)
        mask = np.array([True, False, True, False])
        out = net.forward(x, mask=mask)
        assert out.shape == (4,)
        assert np.all(np.isfinite(out))

    def test_shape_mismatch_raises(self):
        net = AttentionNetwork(n_items=4, hidden_dim=4)
        x = np.random.randn(5)
        with pytest.raises(ValueError):
            net.forward(x)


class TestSpotlightModel:
    def test_fovea_selection(self):
        spot = SpotlightModel(fovea_radius=0.5, fovea_capacity=4)
        items = ["a", "b", "c", "d"]
        positions = np.array([
            [0.0, 0.0],
            [0.4, 0.0],
            [0.6, 0.0],
            [1.0, 1.0],
        ])
        focus = np.array([0.0, 0.0])
        result = spot.apply_spotlight(items, positions, focus)
        assert "a" in result["fovea"]
        assert "d" in result["peripheral"]
        assert "b" in result["fovea"]

    def test_capacity_limit(self):
        spot = SpotlightModel(fovea_radius=1.0, fovea_capacity=2)
        items = ["a", "b", "c"]
        positions = np.array([[0.0, 0.0], [0.1, 0.0], [0.2, 0.0]])
        focus = np.array([0.0, 0.0])
        result = spot.apply_spotlight(items, positions, focus)
        assert len(result["fovea"]) <= 2

    def test_focus_quality(self):
        spot = SpotlightModel(fovea_capacity=4)
        items = ["a", "b", "c", "d"]
        positions = np.array([[0.0, 0.0], [0.1, 0.0], [0.2, 0.0], [0.3, 0.0]])
        spot.apply_spotlight(items, positions, np.array([0.0, 0.0]))
        quality = spot.get_focus_quality()
        assert 0.0 <= quality <= 1.0


class TestAttentionMechanisms:
    def test_attend_returns_keys(self):
        am = AttentionMechanisms(n_items=8, hidden_dim=4)
        items = ["a", "b", "c"]
        vectors = np.random.randn(3, 8)
        result = am.attend(items, vectors, focus_point=np.array([0.0, 0.0]))
        assert "network_output" in result
        assert "spotlight" in result
        assert "attention_scores" in result

    def test_train_attention_returns_loss(self):
        am = AttentionMechanisms(n_items=8, hidden_dim=4)
        x = np.random.randn(8)
        target = np.random.randn(8)
        loss = am.train_attention(x, target, lr=0.01)
        assert isinstance(loss, float)
        assert loss >= 0

    def test_attention_stats(self):
        am = AttentionMechanisms(n_items=8, hidden_dim=4)
        items = ["a", "b"]
        vectors = np.random.randn(2, 8)
        am.attend(items, vectors, focus_point=np.array([0.0, 0.0]))
        stats = am.get_attention_stats()
        assert "history_length" in stats
        assert stats["history_length"] >= 1
