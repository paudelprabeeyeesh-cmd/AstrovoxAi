import pytest
from active_learning.query_strategy import QueryStrategy
from active_learning.uncertainty_sampler import UncertaintySampler


class TestUncertaintySampler:
    def test_default_strategy(self):
        sampler = UncertaintySampler()
        assert sampler.strategy == QueryStrategy.UNCERTAINTY

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            UncertaintySampler("invalid")

    def test_uncertainty_score(self):
        sampler = UncertaintySampler(QueryStrategy.UNCERTAINTY)
        assert sampler.score([0.9, 0.1]) == pytest.approx(0.1)
        assert sampler.score([0.5, 0.5]) == pytest.approx(0.5)
        assert sampler.score([1.0, 0.0]) == pytest.approx(0.0)

    def test_entropy_score(self):
        sampler = UncertaintySampler(QueryStrategy.ENTROPY)
        score = sampler.score([0.5, 0.5])
        assert score > 0.0
        uniform = sampler.score([0.25, 0.25, 0.25, 0.25])
        certain = sampler.score([0.99, 0.01])
        assert uniform > certain

    def test_margin_score(self):
        sampler = UncertaintySampler(QueryStrategy.MARGIN)
        assert sampler.score([0.9, 0.1]) == pytest.approx(0.8)
        assert sampler.score([0.5, 0.5]) == pytest.approx(0.0)

    def test_random_score_range(self):
        sampler = UncertaintySampler(QueryStrategy.RANDOM)
        scores = [sampler.score([0.5, 0.5]) for _ in range(50)]
        assert any(s != scores[0] for s in scores)

    def test_sample_indices_uncertainty(self):
        sampler = UncertaintySampler(QueryStrategy.UNCERTAINTY)
        probas = [[0.9, 0.1], [0.6, 0.4], [0.5, 0.5], [0.1, 0.9]]
        indices = sampler.sample_indices(probas, batch_size=2)
        assert len(indices) == 2
        assert all(isinstance(i, int) for i in indices)
        assert len(set(indices)) == len(indices)

    def test_sample_indices_entropy(self):
        sampler = UncertaintySampler(QueryStrategy.ENTROPY)
        probas = [[0.5, 0.5], [0.99, 0.01], [0.1, 0.9]]
        indices = sampler.sample_indices(probas, batch_size=2)
        assert len(indices) == 2
        assert 0 in indices

    def test_sample_indices_margin(self):
        sampler = UncertaintySampler(QueryStrategy.MARGIN)
        probas = [[0.9, 0.1], [0.55, 0.45]]
        indices = sampler.sample_indices(probas, batch_size=2)
        assert len(indices) == 2

    def test_sample_indices_random(self):
        sampler = UncertaintySampler(QueryStrategy.RANDOM)
        probas = [[0.9, 0.1], [0.6, 0.4], [0.5, 0.5]]
        indices = sampler.sample_indices(probas, batch_size=2)
        assert len(indices) == 2

    def test_sample_batch_larger_than_pool(self):
        sampler = UncertaintySampler(QueryStrategy.UNCERTAINTY)
        probas = [[0.5, 0.5]]
        indices = sampler.sample_indices(probas, batch_size=10)
        assert len(indices) == 1

    def test_query_log_records_selections(self):
        sampler = UncertaintySampler(QueryStrategy.UNCERTAINTY)
        probas = [[0.9, 0.1], [0.5, 0.5], [0.1, 0.9]]
        sampler.sample_indices(probas, batch_size=2)
        log = sampler.get_query_log()
        assert len(log) == 2
        assert all("index" in entry for entry in log)
        assert all("score" in entry for entry in log)
        assert all(entry["strategy"] == QueryStrategy.UNCERTAINTY for entry in log)

    def test_clear_log(self):
        sampler = UncertaintySampler(QueryStrategy.UNCERTAINTY)
        probas = [[0.5, 0.5]]
        sampler.sample_indices(probas, batch_size=1)
        assert len(sampler.get_query_log()) == 1
        sampler.clear_log()
        assert len(sampler.get_query_log()) == 0

    def test_expected_learning_gain_strategy(self):
        sampler = UncertaintySampler(QueryStrategy.EXPECTED_LEARNING_GAIN)
        score = sampler.score([0.5, 0.5])
        assert score > 0.0
