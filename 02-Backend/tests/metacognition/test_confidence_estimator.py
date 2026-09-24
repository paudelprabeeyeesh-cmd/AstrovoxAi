import math

from metacognition.confidence_estimator import ConfidenceEstimator, ConfidenceEstimate


def test_record_sample():
    est = ConfidenceEstimator()
    est.record_sample("key1", 0.9)
    assert "key1" in est.history


def test_estimate_no_samples():
    est = ConfidenceEstimator()
    result = est.estimate("key1")
    assert result.score == 0.5
    assert result.sample_count == 0


def test_estimate_with_samples():
    est = ConfidenceEstimator()
    est.record_sample("key1", 0.8)
    est.record_sample("key1", 0.9)
    result = est.estimate("key1")
    assert math.isclose(result.score, 0.85)
    assert result.sample_count == 2


def test_estimate_with_dimension():
    est = ConfidenceEstimator()
    est.record_sample("key1", 0.8, dimension="accuracy")
    est.record_sample("key1", 0.9, dimension="accuracy")
    result = est.estimate("key1")
    assert "accuracy" in result.dimensions
    assert math.isclose(result.dimensions["accuracy"], 0.85)


def test_bayesian_estimate():
    est = ConfidenceEstimator(prior_strength=2.0)
    est.record_sample("key1", 0.8)
    est.record_sample("key1", 0.9)
    result = est.bayesian_estimate("key1", prior=0.5)
    assert 0.0 <= result.score <= 1.0
    assert result.sample_count == 2


def test_bayesian_estimate_no_samples():
    est = ConfidenceEstimator()
    result = est.bayesian_estimate("key1", prior=0.3)
    assert result.score == 0.3


def test_calibration_error():
    est = ConfidenceEstimator()
    est.record_sample("key1", 0.8)
    error = est.calibration_error("key1", 0.7)
    assert math.isclose(error, 0.1)


def test_reliability():
    est = ConfidenceEstimator(min_samples=2)
    est.record_sample("key1", 0.8)
    rel = est.reliability("key1")
    assert rel == 0.0
    est.record_sample("key1", 0.9)
    rel = est.reliability("key1")
    assert rel >= 0.0


def test_confidence_interval():
    est = ConfidenceEstimator()
    est.record_sample("key1", 0.8)
    est.record_sample("key1", 0.9)
    ci = est.confidence_interval("key1")
    assert "lower" in ci
    assert "upper" in ci
    assert 0.0 <= ci["lower"] <= ci["upper"] <= 1.0


def test_confidence_interval_no_samples():
    est = ConfidenceEstimator()
    ci = est.confidence_interval("key1")
    assert ci["lower"] == 0.0
    assert ci["upper"] == 1.0


def test_reliability_sufficient_samples():
    est = ConfidenceEstimator(min_samples=2)
    est.record_sample("key1", 0.8)
    est.record_sample("key1", 0.8)
    rel = est.reliability("key1")
    assert rel > 0.0


def test_estimate_multiple_dimensions():
    est = ConfidenceEstimator()
    est.record_sample("key1", 0.8, dimension="accuracy")
    est.record_sample("key1", 0.9, dimension="accuracy")
    est.record_sample("key1", 0.7, dimension="speed")
    result = est.estimate("key1")
    assert "accuracy" in result.dimensions
    assert "speed" in result.dimensions
    assert math.isclose(result.dimensions["accuracy"], 0.85)
    assert math.isclose(result.dimensions["speed"], 0.7)


def test_record_sample_dimension_new_key():
    est = ConfidenceEstimator()
    est.record_sample("key1", 0.8, dimension="accuracy")
    assert "key1" in est.dimensions
    assert "accuracy" in est.dimensions["key1"]


def test_estimate_variance_single_sample():
    est = ConfidenceEstimator()
    est.record_sample("key1", 0.8)
    result = est.estimate("key1")
    assert result.variance == 0.25


def test_estimate_variance_multiple_samples():
    est = ConfidenceEstimator()
    est.record_sample("key1", 0.8)
    est.record_sample("key1", 0.9)
    result = est.estimate("key1")
    assert result.variance > 0.0


def test_bayesian_estimate_variance():
    est = ConfidenceEstimator(prior_strength=1.0)
    est.record_sample("key1", 0.8)
    est.record_sample("key1", 0.9)
    result = est.bayesian_estimate("key1", prior=0.5)
    assert result.variance >= 0.0
