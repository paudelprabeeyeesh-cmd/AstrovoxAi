import pytest
from mental_simulation.counterfactual_reasoner import CounterfactualReasoner, Counterfactual


class TestCounterfactualReasoner:
    def test_evaluate_likelihood(self):
        reasoner = CounterfactualReasoner(base_probabilities={"rain": 0.2})
        likelihood = reasoner.evaluate("cloud", "rain", {"effect_strength": 0.5})
        assert 0.0 <= likelihood <= 1.0

    def test_alternate_history(self):
        reasoner = CounterfactualReasoner()
        history = ["a", "b", "c"]
        new_history = reasoner.alternate_history(history, "b", "x")
        assert new_history == ["a", "x", "c"]

    def test_alternate_history_missing_pivot(self):
        reasoner = CounterfactualReasoner()
        history = ["a", "b"]
        new_history = reasoner.alternate_history(history, "z", "x")
        assert new_history == ["a", "b"]

    def test_evaluate_records_counterfactual(self):
        reasoner = CounterfactualReasoner()
        reasoner.evaluate("fire", "smoke", {"effect_strength": 0.3})
        assert len(reasoner.counterfactuals) == 1
        assert reasoner.counterfactuals[0].antecedent == "fire"
