import numpy as np
from ..self_improvement import SelfImprovement, Capability


class TestCapability:
    def test_record_performance(self):
        cap = Capability(name="test")
        cap.record_performance(0.7)
        assert cap.level == 0.7
        assert len(cap.history) == 1

    def test_clamping(self):
        cap = Capability(name="test")
        cap.record_performance(1.5)
        assert cap.level == 1.0
        cap.record_performance(-0.5)
        assert cap.level == 0.0


class TestSelfImprovement:
    def test_bootstrap(self):
        si = SelfImprovement()
        cap = si.bootstrap_capability("reasoning", 0.2)
        assert cap.level == 0.2
        assert "reasoning" in si.capabilities

    def test_evaluate_and_improve(self):
        si = SelfImprovement()
        cap, improvement = si.evaluate_and_improve("math", 0.5)
        assert cap.level == 0.5
        assert si.iteration == 1
        assert len(si.improvement_log) == 1

    def test_identify_weaknesses(self):
        si = SelfImprovement(bootstrap_threshold=0.4)
        si.bootstrap_capability("weak", 0.1)
        si.bootstrap_capability("strong", 0.8)
        weaknesses = si.identify_weaknesses()
        assert "weak" in weaknesses
        assert "strong" not in weaknesses

    def test_improvement_trajectory(self):
        si = SelfImprovement()
        si.evaluate_and_improve("skill", 0.3)
        si.evaluate_and_improve("skill", 0.6)
        traj = si.get_improvement_trajectory("skill")
        assert len(traj) == 2
        assert np.isclose(traj[0], 0.3)

    def test_recursive_reflection(self):
        si = SelfImprovement(bootstrap_threshold=0.3)
        si.bootstrap_capability("a", 0.1)
        si.bootstrap_capability("b", 0.9)
        result = si.recursive_reflection()
        assert "weaknesses" in result
        assert "a" in result["weaknesses"]

    def test_improvement_rate_computed(self):
        si = SelfImprovement()
        si.evaluate_and_improve("skill", 0.2)
        si.evaluate_and_improve("skill", 0.4)
        si.evaluate_and_improve("skill", 0.6)
        cap = si.capabilities["skill"]
        assert cap.improvement_rate > 0
