import numpy as np
import pytest
from ..continual_adaptation import ContinualAdaptation


class TestContinualAdaptation:
    def test_initial_adapt(self):
        ca = ContinualAdaptation(dim=4)
        signal = np.array([1.0, 2.0, 3.0, 4.0])
        weights, reward = ca.adapt(signal, 0.5)
        assert weights.shape == (4,)
        assert reward == 0.5

    def test_get_current_model(self):
        ca = ContinualAdaptation(dim=4)
        ca.adapt(np.array([1.0, 0.0, 0.0, 0.0]), 0.1)
        ca.adapt(np.array([0.0, 1.0, 0.0, 0.0]), 0.9)
        model = ca.get_current_model()
        assert model.shape == (4,)

    def test_measure_plasticity(self):
        ca = ContinualAdaptation(dim=4)
        assert np.isclose(ca.measure_plasticity(), 1.0)
        for i in range(10):
            ca.adapt(np.array([float(i)] * 4), 0.5)
        assert ca.measure_plasticity() >= 0.0

    def test_adaptation_stats(self):
        ca = ContinualAdaptation(dim=4)
        ca.adapt(np.ones(4), 0.7)
        stats = ca.get_adaptation_stats()
        assert "step" in stats
        assert stats["state_count"] == 1

    def test_input_padding(self):
        ca = ContinualAdaptation(dim=8)
        signal = np.array([1.0, 2.0])
        weights, _ = ca.adapt(signal, 0.5)
        assert weights.shape == (8,)

    def test_max_states_enforced(self):
        ca = ContinualAdaptation(dim=2, max_states=3)
        for i in range(10):
            ca.adapt(np.array([float(i), float(i)]), float(i) / 10.0)
        assert len(ca.states) <= 3
