import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.alignment_at_scale import (
    AlignmentAtScale,
    ValueVector,
)


class TestAlignmentAtScale:
    def test_register_value_vector(self):
        align = AlignmentAtScale(value_dim=32)
        vv = align.register_value_vector(np.random.randn(32), confidence=0.9, source="human", scalability=0.7)
        assert isinstance(vv, ValueVector)
        assert vv.source == "human"
        assert vv.values.shape == (32,)

    def test_scalable_oversight_empty(self):
        align = AlignmentAtScale(value_dim=32)
        result = align.scalable_oversight(np.random.randn(32), n_overseers=5)
        assert result["alignment_score"] == 0.0

    def test_scalable_oversight_with_values(self):
        align = AlignmentAtScale(value_dim=32)
        align.register_value_vector(np.random.randn(32), confidence=0.9, source="human")
        align.register_value_vector(np.random.randn(32), confidence=0.8, source="society")
        result = align.scalable_oversight(np.random.randn(32), n_overseers=10)
        assert 0.0 <= result["alignment_score"] <= 1.0
        assert result["n_overseers"] == 10

    def test_scalable_value_learning(self):
        align = AlignmentAtScale(value_dim=32)
        align.register_value_vector(np.random.randn(32), confidence=0.9, source="human")
        system_out = np.random.randn(32)
        feedback = np.random.randn(32)
        result = align.scalable_value_learning(system_out, feedback, lr=0.01)
        assert "loss" in result
        assert "mean_update" in result
        assert len(align.alignment_history) == 1

    def test_measure_alignment_robustness(self):
        align = AlignmentAtScale(value_dim=32)
        align.register_value_vector(np.random.randn(32), confidence=0.9, source="human")
        system_out = np.random.randn(32)
        result = align.measure_alignment_robustness(system_out, perturbations=50)
        assert "robustness" in result
        assert 0.0 <= result["robustness"] <= 1.0

    def test_alignment_stats(self):
        align = AlignmentAtScale(value_dim=32)
        align.register_value_vector(np.random.randn(32), confidence=0.9, source="human")
        stats = align.get_alignment_stats()
        assert stats["value_vectors"] == 1
        assert stats["mean_confidence"] == pytest.approx(0.9)

    def test_register_value_vector_pads(self):
        align = AlignmentAtScale(value_dim=32)
        vv = align.register_value_vector(np.random.randn(16), confidence=0.9, source="human")
        assert vv.values.shape == (32,)

    def test_scalable_oversight_pads_output(self):
        align = AlignmentAtScale(value_dim=32)
        align.register_value_vector(np.random.randn(32), confidence=0.9, source="human")
        result = align.scalable_oversight(np.random.randn(16), n_overseers=5)
        assert 0.0 <= result["alignment_score"] <= 1.0

    def test_scalable_value_learning_pads_inputs(self):
        align = AlignmentAtScale(value_dim=32)
        align.register_value_vector(np.random.randn(32), confidence=0.9, source="human")
        result = align.scalable_value_learning(np.random.randn(16), np.random.randn(16), lr=0.01)
        assert "loss" in result

    def test_scalable_value_learning_creates_default_vector(self):
        align = AlignmentAtScale(value_dim=32)
        result = align.scalable_value_learning(np.random.randn(32), np.random.randn(32), lr=0.01)
        assert len(align.value_vectors) == 1

    def test_alignment_stats_empty(self):
        align = AlignmentAtScale(value_dim=32)
        stats = align.get_alignment_stats()
        assert stats["value_vectors"] == 0
        assert stats["alignment_checks"] == 0
