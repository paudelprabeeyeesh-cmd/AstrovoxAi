import math

import pytest

from transfer_learning.similarity_estimator import SimilarityEstimator, SimilarityResult


class TestSimilarityEstimator:
    def test_cosine_identical(self):
        estimator = SimilarityEstimator()
        result = estimator.cosine([1.0, 2.0], [1.0, 2.0])
        assert result.method == "cosine"
        assert math.isfinite(result.score)
        assert math.isclose(result.score, 1.0, rel_tol=1e-6)

    def test_cosine_orthogonal(self):
        estimator = SimilarityEstimator()
        result = estimator.cosine([1.0, 0.0], [0.0, 1.0])
        assert math.isfinite(result.score)

    def test_euclidean(self):
        estimator = SimilarityEstimator()
        result = estimator.euclidean([0.0, 0.0], [3.0, 4.0])
        assert result.method == "euclidean"
        assert math.isfinite(result.score)

    def test_manhattan(self):
        estimator = SimilarityEstimator()
        result = estimator.manhattan([0.0, 0.0], [1.0, 1.0])
        assert result.method == "manhattan"
        assert math.isfinite(result.score)

    def test_pearson(self):
        estimator = SimilarityEstimator()
        result = estimator.pearson([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert result.method == "pearson"
        assert math.isfinite(result.score)

    def test_jaccard(self):
        estimator = SimilarityEstimator()
        result = estimator.jaccard([1.0, 2.0], [2.0, 3.0])
        assert result.method == "jaccard"
        assert math.isfinite(result.score)

    def test_estimate_method(self):
        estimator = SimilarityEstimator(method="cosine")
        result = estimator.estimate([1.0, 0.0], [0.0, 1.0])
        assert result.method == "cosine"

    def test_estimate_override(self):
        estimator = SimilarityEstimator(method="cosine")
        result = estimator.estimate([1.0, 0.0], [0.0, 1.0], method="euclidean")
        assert result.method == "euclidean"

    def test_estimate_invalid_method(self):
        estimator = SimilarityEstimator()
        with pytest.raises(ValueError):
            estimator.estimate([1.0, 0.0], [0.0, 1.0], method="invalid")

    def test_validation_length_mismatch(self):
        estimator = SimilarityEstimator()
        with pytest.raises(ValueError):
            estimator.cosine([1.0], [1.0, 2.0])

    def test_validation_empty(self):
        estimator = SimilarityEstimator()
        with pytest.raises(ValueError):
            estimator.cosine([], [])

    def test_history(self):
        estimator = SimilarityEstimator()
        estimator.cosine([1.0, 0.0], [0.0, 1.0])
        assert len(estimator.history) == 1

    def test_summary(self):
        estimator = SimilarityEstimator()
        assert estimator.summary()["count"] == 0
        estimator.cosine([1.0, 0.0], [0.0, 1.0])
        summary = estimator.summary()
        assert summary["count"] == 1
