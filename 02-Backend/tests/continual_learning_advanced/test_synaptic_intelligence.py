import math
import pytest
from continual_learning_advanced.synaptic_intelligence import SynapticIntelligence, SIState


class TestSynapticIntelligence:
    def test_initialization(self):
        si = SynapticIntelligence(epsilon=1e-3, damping=1e-4)
        assert si.epsilon == 1e-3
        assert si.damping == 1e-4
        assert si.omega == {}
        assert si.importance == {}
        assert si.task_states == {}

    def test_register_params(self):
        si = SynapticIntelligence()
        si.register_params({"W": 1.0, "b": 0.5})
        assert "W" in si.omega
        assert "b" in si.omega
        assert si.omega["W"] == 0.0
        assert si.grad_history["W"] == []

    def test_record_step_then_compute_importance(self):
        si = SynapticIntelligence()
        params = {"W": 1.0, "b": 0.0}
        si.register_params(params)
        si.record_step(params, {"W": 0.1, "b": -0.2})
        new_params = {"W": 1.1, "b": -0.1}
        si.record_step(new_params, {"W": 0.2, "b": 0.1})
        imp = si.compute_importance(new_params)
        assert "W" in imp
        assert "b" in imp
        assert imp["W"] > 0

    def test_penalty_when_changed(self):
        si = SynapticIntelligence()
        params = {"W": 1.0}
        si.register_params(params)
        si.record_step(params, {"W": 0.5})
        new_params = {"W": 2.0}
        si.compute_importance(new_params)
        p = si.penalty(new_params)
        assert p >= 0.0

    def test_penalty_zero_at_old_params(self):
        si = SynapticIntelligence()
        params = {"W": 1.0}
        si.register_params(params)
        si.record_step(params, {"W": 0.5})
        si.compute_importance(params)
        assert si.penalty(params) == 0.0

    def test_consolidate_and_get_task_importance(self):
        si = SynapticIntelligence()
        params = {"W": 1.0, "b": 0.5}
        si.register_params(params)
        si.record_step(params, {"W": 0.1, "b": -0.1})
        new_params = {"W": 1.2, "b": 0.6}
        si.compute_importance(new_params)
        si.consolidate_task("task1", new_params)
        task_imp = si.get_task_importance("task1")
        assert "W" in task_imp
        assert si.get_task_importance("unknown") == {}
