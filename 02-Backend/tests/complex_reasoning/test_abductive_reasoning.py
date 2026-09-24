import pytest
from complex_reasoning.abductive_reasoning import Hypothesis, AbductiveEngine


class TestHypothesis:
    def test_creation(self):
        h = Hypothesis("Test", prior=0.2, explanation_power=0.5)
        assert h.description == "Test"
        assert h.prior == 0.2
        assert h.explanation_power == 0.5
        assert h.likelihood == 0.0
        assert h.posterior == 0.0

    def test_update_posterior(self):
        h = Hypothesis("H", prior=0.1)
        result = h.update_posterior(0.8)
        assert h.likelihood == 0.8
        assert h.posterior == pytest.approx(0.08)
        assert result == pytest.approx(0.08)


class TestAbductiveEngine:
    def test_add_hypothesis(self):
        engine = AbductiveEngine()
        engine.add_hypothesis(Hypothesis("Rain"))
        assert len(engine.hypotheses) == 1

    def test_set_observations(self):
        engine = AbductiveEngine()
        engine.set_observations(["grass wet", "sky dark"])
        assert len(engine.observations) == 2

    def test_generate_best_returns_top_k(self):
        engine = AbductiveEngine()
        engine.set_observations(["wet grass", "dark sky"])
        engine.add_hypothesis(Hypothesis("Rain", prior=0.3))
        engine.add_hypothesis(Hypothesis("Sprinklers", prior=0.1))
        results = engine.generate_best(top_k=1)
        assert len(results) == 1
        assert results[0][0].description == "Rain"

    def test_generate_best_updates_posterior(self):
        engine = AbductiveEngine()
        engine.set_observations(["wet grass"])
        engine.add_hypothesis(Hypothesis("Rain", prior=0.1))
        results = engine.generate_best(top_k=1)
        h, score = results[0]
        assert h.likelihood >= 0.0
        assert h.posterior == pytest.approx(h.prior * h.likelihood)

    def test_beam_search_depth(self):
        engine = AbductiveEngine()
        engine.add_hypothesis(Hypothesis("Rain"))
        engine.add_hypothesis(Hypothesis("Wind"))
        result = engine.beam_search(depth=2)
        assert isinstance(result, list)
        assert len(result) <= engine.beam_width

    def test_empty_hypotheses(self):
        engine = AbductiveEngine()
        assert engine.generate_best() == []
        assert engine.beam_search() == []
