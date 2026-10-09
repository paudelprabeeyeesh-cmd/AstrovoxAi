import pytest
from advanced_reasoning.counterfactual_reasoner import CounterfactualReasoner, World, Counterfactual


class TestCounterfactualReasoner:
    def test_generate_counterfactual(self):
        reasoner = CounterfactualReasoner()
        reasoner.add_world(World(facts={"A": "true"}, name="base"))
        cf = reasoner.generate("A is false", "B is false")
        assert cf.antecedent == "A is false"
        assert cf.consequent == "B is false"
        assert "A is false" in cf.alternative_world.facts

    def test_missing_world_raises(self):
        reasoner = CounterfactualReasoner()
        with pytest.raises(KeyError):
            reasoner.generate("A", "B", base_name="missing")

    def test_evaluate_counterfactual(self):
        reasoner = CounterfactualReasoner()
        reasoner.add_world(World(facts={}, name="base"))
        cf = reasoner.generate("X", "Y")
        result = reasoner.evaluate(cf.id)
        assert "consistency" in result
        assert 0.0 <= result["consistency"] <= 1.0

    def test_default_base_world(self):
        reasoner = CounterfactualReasoner()
        assert "base" in reasoner.worlds
        assert reasoner.worlds["base"].facts == {}

    def test_add_multiple_worlds(self):
        reasoner = CounterfactualReasoner()
        reasoner.add_world(World(facts={"temp": "hot"}, name="tropical"))
        reasoner.add_world(World(facts={"temp": "cold"}, name="arctic"))
        assert reasoner.worlds["tropical"].facts["temp"] == "hot"
        assert reasoner.worlds["arctic"].facts["temp"] == "cold"

    def test_counterfactual_count(self):
        reasoner = CounterfactualReasoner()
        reasoner.add_world(World(facts={}, name="base"))
        reasoner.generate("A", "B")
        reasoner.generate("C", "D")
        assert len(reasoner.counterfactuals) == 2
