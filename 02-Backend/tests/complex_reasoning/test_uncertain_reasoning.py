import pytest
from complex_reasoning.uncertain_reasoning import BayesNet, ProbabilisticInference, UncertaintyEngine, InferenceEngine


class TestBayesNet:
    def test_add_prior(self):
        net = BayesNet()
        net.add_prior("Rain", 0.3)
        assert net.priors["Rain"] == pytest.approx(0.3)

    def test_add_likelihood(self):
        net = BayesNet()
        net.add_likelihood("Rain", "Wet", 0.8)
        assert net.likelihoods["Rain"]["Wet"] == pytest.approx(0.8)

    def test_bayes_rule(self):
        net = BayesNet()
        post = net.bayes_rule(0.1, 0.8, 0.3)
        assert 0.0 < post < 1.0

    def test_posterior(self):
        net = BayesNet()
        net.add_prior("Rain", 0.2)
        net.add_likelihood("Rain", "Wet_true", 0.9)
        net.add_likelihood("Rain", "Wet_false", 0.2)
        post = net.posterior("Rain", "Wet")
        assert 0.0 < post < 1.0

    def test_update(self):
        net = BayesNet()
        net.add_prior("Rain", 0.2)
        net.add_likelihood("Rain", "Wet_true", 0.9)
        net.add_likelihood("Rain", "Wet_false", 0.2)
        val = net.update("Rain", "Wet")
        assert val == pytest.approx(net.posteriors["Rain"])

    def test_likelihood_weighting(self):
        net = BayesNet()
        net.add_prior("A", 0.6)
        net.add_likelihood("A", "e", 0.8)
        result = net.likelihood_weighting("A", n_samples=500)
        assert 0.0 <= result <= 1.0


class TestProbabilisticInference:
    def test_update_belief(self):
        inf = ProbabilisticInference()
        inf.add_observation("Rain", 0.3)
        inf.add_evidence("Rain", "Wet", 0.9)
        result = inf.update_belief("Rain", "Wet")
        assert 0.0 < result < 1.0

    def test_confidence(self):
        inf = ProbabilisticInference()
        inf.add_observation("Rain", 0.9)
        conf = inf.confidence("Rain")
        assert conf > 0.0

    def test_predict(self):
        inf = ProbabilisticInference()
        inf.add_observation("Rain", 0.2)
        inf.add_evidence("Rain", "Wet", 0.95)
        assert 0.0 <= inf.predict("Rain", "Wet") <= 1.0


class TestUncertaintyEngine:
    def test_add_data(self):
        engine = UncertaintyEngine()
        engine.add_data("Temp", [20.0, 21.0, 19.5])
        assert "Temp" in engine.probabilities
        assert engine.noise_models["Temp"] > 0.0

    def test_str(self):
        engine = UncertaintyEngine()
        s = str(engine)
        assert "UncertaintyEngine" in s


class TestInferenceEngine:
    def test_add_prior_and_likelihood(self):
        engine = InferenceEngine()
        engine.add_prior("A", 0.5)
        engine.add_likelihood("A", "e", 0.7)
        val = engine.update("A", "e")
        assert 0.0 < val < 1.0
