import math

import pytest

from transfer_learning.domain_adapter import AdaptationConfig, DomainAdapter, DomainProfile


class TestDomainProfile:
    def test_profile_creation(self):
        profile = DomainProfile(name="source", feature_mean=[0.5], feature_std=[1.0])
        assert profile.name == "source"
        assert profile.feature_mean == [0.5]
        assert profile.sample_count == 0


class TestAdaptationConfig:
    def test_default_config(self):
        config = AdaptationConfig()
        assert config.gamma == 0.01
        assert config.max_iterations == 100
        assert config.tolerance == 1e-6


class TestDomainAdapter:
    def test_adapter_initialization(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        assert adapter.source.name == "src"
        assert adapter.target.name == "tgt"
        assert adapter.adaptation_matrix is None

    def test_fit(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        source = [[0.0, 1.0], [1.0, 0.0], [2.0, 3.0]]
        target = [[0.5, 1.5], [1.5, 0.5]]
        adapter.fit(source, target)
        assert adapter.adaptation_matrix is not None
        assert adapter.source.sample_count == 3
        assert adapter.target.sample_count == 2

    def test_adapt(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        adapter.fit([[0.0, 1.0], [1.0, 0.0]], [[0.5, 1.5]])
        result = adapter.adapt([1.0, 1.0])
        assert len(result) == 2
        assert adapter.adaptation_matrix is not None

    def test_batch_adapt(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        adapter.fit([[0.0, 1.0]], [[0.5, 1.5]])
        batch = adapter.batch_adapt([[0.0, 1.0], [1.0, 0.0]])
        assert len(batch) == 2

    def test_fit_empty_samples(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        with pytest.raises(ValueError):
            adapter.fit([], [[0.0]])

    def test_adapt_before_fit(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        with pytest.raises(RuntimeError):
            adapter.adapt([1.0, 2.0])

    def test_summary(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        adapter.fit([[0.0, 1.0]], [[0.5, 1.5]])
        summary = adapter.summary()
        assert summary["source_domain"] == "src"
        assert summary["target_domain"] == "tgt"
        assert summary["fitted"] is True

    def test_custom_config(self):
        config = AdaptationConfig(gamma=0.1, max_iterations=200, tolerance=1e-4)
        assert config.gamma == 0.1
        assert config.max_iterations == 200
        assert config.tolerance == 1e-4

    def test_fit_inconsistent_source_dimensions(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        with pytest.raises(ValueError):
            adapter.fit([[0.0, 1.0], [2.0]], [[0.5, 1.5]])

    def test_fit_inconsistent_target_dimensions(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        with pytest.raises(ValueError):
            adapter.fit([[0.0, 1.0]], [[0.5, 1.5], [2.0]])

    def test_adapt_wrong_sample_dimension(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        adapter.fit([[0.0, 1.0]], [[0.5, 1.5]])
        with pytest.raises(ValueError):
            adapter.adapt([1.0, 2.0, 3.0])

    def test_adaptation_log(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        adapter.fit([[0.0, 1.0]], [[0.5, 1.5]])
        assert len(adapter.adaptation_log) == 1
        assert adapter.adaptation_log[0]["action"] == "fit"
        adapter.adapt([0.0, 1.0])
        assert len(adapter.adaptation_log) == 2
        assert adapter.adaptation_log[1]["action"] == "adapt"

    def test_compute_mean(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        mean = adapter._compute_mean([[1.0, 2.0], [3.0, 4.0]])
        assert math.isclose(mean[0], 2.0)
        assert math.isclose(mean[1], 3.0)

    def test_compute_std(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        mean = [1.0, 2.0]
        std = adapter._compute_std([[1.0, 2.0], [3.0, 4.0]], mean)
        assert std[0] > 0.0
        assert std[1] > 0.0

    def test_batch_adapt_empty(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        adapter.fit([[0.0, 1.0]], [[0.5, 1.5]])
        result = adapter.batch_adapt([])
        assert result == []

    def test_summary_adaptation_steps(self):
        adapter = DomainAdapter(source_domain="src", target_domain="tgt")
        adapter.fit([[0.0, 1.0]], [[0.5, 1.5]])
        adapter.adapt([0.0, 1.0])
        adapter.adapt([1.0, 0.0])
        summary = adapter.summary()
        assert summary["adaptation_steps"] == 3
