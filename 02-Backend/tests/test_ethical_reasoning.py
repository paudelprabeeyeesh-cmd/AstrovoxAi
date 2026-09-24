import pytest
from ethical_reasoning.ethical_engine import EthicalEngine, Principle


class TestEthicalEngine:
    def test_analyze_basic(self):
        engine = EthicalEngine()
        result = engine.analyze("help people", stakeholders=["users", "admins"])
        assert 0.0 <= result.risk_score <= 1.0
        assert len(result.principles_applied) > 0

    def test_high_risk_recommendation(self):
        engine = EthicalEngine()
        result = engine.analyze("harm people", stakeholders=["victims"])
        assert result.risk_score > 0.3
        assert "caution" in result.recommendation.lower() or "do not" in result.recommendation.lower()

    def test_value_conflicts(self):
        engine = EthicalEngine()
        result = engine.analyze("action", stakeholders=["a"])
        conflicts = engine.value_conflicts(result)
        assert isinstance(conflicts, list)

    def test_update_alignment(self):
        engine = EthicalEngine()
        engine.update_alignment("beneficence", 0.9)
        assert engine.value_alignments["beneficence"] == 0.9

    def test_confidence_in_range(self):
        engine = EthicalEngine()
        result = engine.analyze("test action", stakeholders=["s1"])
        assert 0.0 <= result.confidence <= 1.0

    def test_custom_principles(self):
        custom = [Principle("fairness", "Be fair", weight=2.0)]
        engine = EthicalEngine(principles=custom)
        result = engine.analyze("fairness test", stakeholders=["a"])
        assert "fairness" in result.values_alignment
