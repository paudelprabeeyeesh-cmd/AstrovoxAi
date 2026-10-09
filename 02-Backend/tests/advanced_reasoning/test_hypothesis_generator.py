import pytest
from advanced_reasoning.hypothesis_generator import HypothesisGenerator, Observation, Hypothesis


class TestHypothesisGenerator:
    def test_generate_hypothesis(self):
        gen = HypothesisGenerator()
        obs1 = Observation(id="o1", description="the ground is wet")
        gen.add_observation(obs1)
        hypotheses = gen.generate(["o1"])
        assert len(hypotheses) == 1
        assert hypotheses[0].statement
        assert "o1" in hypotheses[0].evidence_ids

    def test_generate_multiple(self):
        gen = HypothesisGenerator()
        obs1 = Observation(id="o1", description="apple falls")
        obs2 = Observation(id="o2", description="gravity exists")
        gen.add_observation(obs1)
        gen.add_observation(obs2)
        hypotheses = gen.generate(["o1", "o2"])
        assert len(hypotheses) == 2

    def test_refine_hypothesis(self):
        gen = HypothesisGenerator()
        obs = Observation(id="o1", description="sky is blue")
        gen.add_observation(obs)
        h = gen.generate(["o1"])[0]
        result = gen.refine(h.id, ["o1"])
        assert result is not None
        assert result.confidence > 0.5

    def test_generate_empty_ids(self):
        gen = HypothesisGenerator()
        hypotheses = gen.generate([])
        assert hypotheses == []

    def test_observations_stored(self):
        gen = HypothesisGenerator()
        obs = Observation(id="o1", description="fire is hot")
        gen.add_observation(obs)
        assert "o1" in gen.observations
        assert gen.observations["o1"].description == "fire is hot"

    def test_refine_missing_hypothesis(self):
        gen = HypothesisGenerator()
        result = gen.refine("h-999", ["o1"])
        assert result is None
