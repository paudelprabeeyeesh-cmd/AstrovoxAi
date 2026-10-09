import numpy as np
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.neuroplasticity import (
    NeuroplasticitySystem,
    LearningRule,
    Metaplasticity,
    Synapse,
)


class TestSynapse:
    def test_clip_within_range(self):
        s = Synapse(weight=2.0, last_update=time.time(), max_weight=1.0, min_weight=-1.0)
        s.clip()
        assert s.weight == pytest.approx(1.0)

    def test_clip_min(self):
        s = Synapse(weight=-2.0, last_update=time.time(), max_weight=1.0, min_weight=-1.0)
        s.clip()
        assert s.weight == pytest.approx(-1.0)


class TestLearningRule:
    def test_hebbian_increases_correlated(self):
        lr = LearningRule(learning_rate=0.1)
        s = Synapse(weight=0.0, last_update=time.time())
        pre = np.array([1.0])
        post = np.array([1.0])
        delta = lr.hebbian(pre, post, s)
        assert s.weight > 0.0
        assert delta > 0.0

    def test_oja_rule(self):
        lr = LearningRule(learning_rate=0.1)
        s = Synapse(weight=0.5, last_update=time.time())
        pre = np.array([1.0])
        post = np.array([1.0])
        delta = lr.oja(pre, post, s)
        assert isinstance(delta, float)

    def test_stdp_returns_delta(self):
        lr = LearningRule(learning_rate=0.1)
        s = Synapse(weight=0.0, last_update=time.time())
        pre = np.array([1.0])
        post = np.array([1.0])
        dt = np.array([[0.01]])
        delta = lr.stdp(pre, post, dt, s)
        assert isinstance(delta, float)


class TestMetaplasticity:
    def test_adjust_threshold_high_activity(self):
        mp = Metaplasticity(sliding_threshold=0.5, homeostatic_rate=0.1)
        new_thresh = mp.adjust_threshold(np.array([0.9, 0.8]), current_threshold=0.5)
        assert new_thresh >= 0.5

    def test_adjust_threshold_low_activity(self):
        mp = Metaplasticity(sliding_threshold=0.5, homeostatic_rate=0.1)
        new_thresh = mp.adjust_threshold(np.array([0.1, 0.2]), current_threshold=0.5)
        assert new_thresh <= 0.5

    def test_homeostatic_scaling(self):
        mp = Metaplasticity()
        synapses = [Synapse(weight=0.1, last_update=time.time()) for _ in range(4)]
        adjustments = mp.homeostatic_scaling(synapses, target_rate=0.5)
        assert len(adjustments) == 4


class TestNeuroplasticitySystem:
    def test_get_weight_matrix(self):
        nps = NeuroplasticitySystem(n_neurons_pre=4, n_neurons_post=4)
        w = nps.get_weight_matrix()
        assert w.shape == (4, 4)

    def test_hebbian_update(self):
        nps = NeuroplasticitySystem(n_neurons_pre=4, n_neurons_post=4)
        pre = np.ones(4)
        post = np.ones(4)
        total_delta = nps.update(pre, post, rule="hebbian")
        assert total_delta >= 0.0

    def test_oja_update(self):
        nps = NeuroplasticitySystem(n_neurons_pre=4, n_neurons_post=4)
        pre = np.ones(4)
        post = np.ones(4)
        total_delta = nps.update(pre, post, rule="oja")
        assert total_delta >= 0.0

    def test_apply_stdp(self):
        nps = NeuroplasticitySystem(n_neurons_pre=4, n_neurons_post=4)
        pre_times = np.array([0.0, 0.01, 0.02, 0.03])
        post_times = np.array([0.005, 0.015, 0.025, 0.035])
        total_delta = nps.apply_stdp(pre_times, post_times)
        assert total_delta >= 0.0

    def test_homeostatic_scale(self):
        nps = NeuroplasticitySystem(n_neurons_pre=4, n_neurons_post=4)
        adjustments = nps.homeostatic_scale(target_rate=0.5)
        assert len(adjustments) == 16

    def test_dimension_mismatch_raises(self):
        nps = NeuroplasticitySystem(n_neurons_pre=4, n_neurons_post=4)
        with pytest.raises(ValueError):
            nps.update(np.ones(3), np.ones(4))

    def test_get_eligibility_matrix(self):
        nps = NeuroplasticitySystem(n_neurons_pre=4, n_neurons_post=4)
        e = nps.get_eligibility_matrix()
        assert e.shape == (4, 4)
