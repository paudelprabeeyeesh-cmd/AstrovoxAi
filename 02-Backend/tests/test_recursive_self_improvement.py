import pytest
import numpy as np
from agi_core.recursive_self_improvement import RecursiveSelfImprovement


class TestRecursiveSelfImprovement:
    def test_propose(self):
        engine = RecursiveSelfImprovement()
        p = engine.propose("reasoning", "Better reasoning", 0.3, 0.5)
        assert p.capability == "reasoning"
        assert p.status == "proposed"

    def test_validate(self):
        engine = RecursiveSelfImprovement()
        p = engine.propose("c", "d", 0.9, 0.1)
        assert not engine.validate(p)
        p2 = engine.propose("c", "d", 0.2, 0.6)
        assert engine.validate(p2)

    def test_apply(self):
        engine = RecursiveSelfImprovement()
        p = engine.propose("c", "d", 0.2, 0.5)
        result = engine.apply(p)
        assert result
        assert p.status == "applied"

    def test_recursive_step(self):
        engine = RecursiveSelfImprovement()
        engine.capability_levels["reasoning"] = 0.3
        new = engine.recursive_step()
        assert len(new) > 0

    def test_capability_report(self):
        engine = RecursiveSelfImprovement()
        report = engine.get_capability_report()
        assert "mean_capability" in report
