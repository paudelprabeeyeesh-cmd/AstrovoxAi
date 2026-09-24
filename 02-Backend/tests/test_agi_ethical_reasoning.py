import pytest
import numpy as np
from agi_core.ethical_reasoning import EthicalReasoner, MoralPrinciple


class TestEthicalReasoner:
    def test_evaluate(self):
        engine = EthicalReasoner()
        state = engine.evaluate("help people", ["users"])
        assert 0.0 <= state.moral_score <= 1.0

    def test_harm_action_low_score(self):
        engine = EthicalReasoner()
        state = engine.evaluate("harm people", ["users"])
        assert state.moral_score < 0.5

    def test_value_conflicts(self):
        engine = EthicalReasoner()
        state = engine.evaluate("action", ["a"])
        assert isinstance(state.value_conflicts, list)

    def test_moral_judgment(self):
        engine = EthicalReasoner()
        result = engine.moral_judgment("test action", ["s1"])
        assert "moral_score" in result
        assert "conflict_severity" in result

    def test_judgment_history(self):
        engine = EthicalReasoner()
        engine.evaluate("a", ["b"])
        engine.evaluate("c", ["d"])
        assert len(engine.judgment_history) == 2
