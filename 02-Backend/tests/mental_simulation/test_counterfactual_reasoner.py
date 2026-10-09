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

    def test_evaluate_uses_base_probabilities(self):
        reasoner = CounterfactualReasoner(base_probabilities={"rain": 0.8})
        likelihood = reasoner.evaluate("cloud", "rain", {"effect_strength": 0.5})
        assert pytest.approx(likelihood, abs=1e-6) == 1.0

    def test_alternate_history_preserves_original(self):
        reasoner = CounterfactualReasoner()
        history = ["a", "b", "c"]
        reasoner.alternate_history(history, "b", "x")
        assert history == ["a", "b", "c"]

    def test_alternate_history_first_occurrence(self):
        reasoner = CounterfactualReasoner()
        history = ["a", "b", "a", "b"]
        new_history = reasoner.alternate_history(history, "b", "x")
        assert new_history == ["a", "x", "a", "b"]

    def test_counterfactual_fields(self):
        reasoner = CounterfactualReasoner()
        reasoner.evaluate("A", "B", {"effect_strength": 0.4})
        cf = reasoner.counterfactuals[0]
        assert cf.antecedent == "A"
        assert cf.consequent == "B"
        assert cf.evidence == {"effect_strength": 0.4}
