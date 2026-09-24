import pytest
from few_shot_learning.similarity_classifier import (
    CosineSimilarityClassifier,
    EuclideanSimilarityClassifier,
    MahalanobisSimilarityClassifier,
    PairwiseSimilarityClassifier,
    SimilarityClassifier,
)


def _simple_data():
    support_x = [[0.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
    support_y = [0, 1, 2]
    query_x = [[1.0, 1.0], [9.0, 9.0], [1.0, 9.0]]
    query_y = [0, 1, 2]
    return support_x, support_y, query_x, query_y


def test_cosine_classifier_perfect():
    support_x, support_y, query_x, query_y = _simple_data()
    clf = CosineSimilarityClassifier()
    clf.fit(support_x, support_y)
    preds = clf.predict(query_x)
    assert preds == query_y


def test_euclidean_classifier_perfect():
    support_x, support_y, query_x, query_y = _simple_data()
    clf = EuclideanSimilarityClassifier()
    clf.fit(support_x, support_y)
    preds = clf.predict(query_x)
    assert preds == query_y


def test_pairwise_classifier_perfect():
    support_x, support_y, query_x, query_y = _simple_data()
    clf = PairwiseSimilarityClassifier()
    clf.fit(support_x, support_y)
    preds = clf.predict(query_x)
    assert preds == query_y


def test_mahalanobis_classifier_perfect():
    support_x, support_y, query_x, query_y = _simple_data()
    clf = MahalanobisSimilarityClassifier()
    clf.fit(support_x, support_y)
    preds = clf.predict(query_x)
    assert preds == query_y


def test_score_returns_accuracy_and_predictions():
    support_x, support_y, query_x, query_y = _simple_data()
    clf = EuclideanSimilarityClassifier()
    clf.fit(support_x, support_y)
    result = clf.score(query_x, query_y)
    assert result["accuracy"] == 1.0
    assert result["predictions"] == query_y


def test_predict_without_fit():
    clf = CosineSimilarityClassifier()
    preds = clf.predict([[1.0, 2.0]])
    assert preds == [0]


def test_classifier_interface():
    clf = EuclideanSimilarityClassifier()
    assert isinstance(clf, SimilarityClassifier)


def test_mahalanobis_fallback_on_singular():
    support_x = [[1.0], [1.0], [2.0], [2.0]]
    support_y = [0, 0, 1, 1]
    clf = MahalanobisSimilarityClassifier()
    clf.fit(support_x, support_y)
    preds = clf.predict([[1.5]])
    assert preds[0] in (0, 1)
