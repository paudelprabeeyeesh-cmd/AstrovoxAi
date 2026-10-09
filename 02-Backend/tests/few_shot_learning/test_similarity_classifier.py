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


def test_vec_norm():
    from few_shot_learning.similarity_classifier import _vec_norm
    assert _vec_norm([3.0, 4.0]) == 5.0
    assert _vec_norm([0.0, 0.0]) == 0.0


def test_vec_dot():
    from few_shot_learning.similarity_classifier import _vec_dot
    assert _vec_dot([1.0, 2.0], [3.0, 4.0]) == 11.0


def test_mat_mul():
    from few_shot_learning.similarity_classifier import _mat_mul
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]
    result = _mat_mul(a, b)
    assert result == [[19.0, 22.0], [43.0, 50.0]]


def test_mat_inv():
    from few_shot_learning.similarity_classifier import _mat_inv
    m = [[4.0, 7.0], [2.0, 6.0]]
    inv = _mat_inv(m)
    expected = [[0.6, -0.7], [-0.2, 0.4]]
    for row1, row2 in zip(inv, expected):
        for a, b in zip(row1, row2):
            assert abs(a - b) < 1e-9


def test_mat_inv_singular():
    from few_shot_learning.similarity_classifier import _mat_inv
    with pytest.raises(ValueError):
        _mat_inv([[1.0, 2.0], [2.0, 4.0]])


def test_predict_without_fit_returns_zeros():
    clf = EuclideanSimilarityClassifier()
    preds = clf.predict([[1.0, 2.0]])
    assert preds == [0]
    clf = PairwiseSimilarityClassifier()
    preds = clf.predict([[1.0, 2.0]])
    assert preds == [0]
    clf = MahalanobisSimilarityClassifier()
    preds = clf.predict([[1.0, 2.0]])
    assert preds == [0]


def test_score_empty_query():
    support_x, support_y, _, _ = _simple_data()
    clf = EuclideanSimilarityClassifier()
    clf.fit(support_x, support_y)
    result = clf.score([], [])
    assert result["accuracy"] == 0.0
    assert result["predictions"] == []


def test_mahalanobis_with_custom_reg():
    support_x = [[0.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
    support_y = [0, 1, 2]
    query_x = [[1.0, 1.0], [9.0, 9.0], [1.0, 9.0]]
    query_y = [0, 1, 2]
    clf = MahalanobisSimilarityClassifier(reg=1e-2)
    clf.fit(support_x, support_y)
    preds = clf.predict(query_x)
    assert preds == query_y


def test_pairwise_is_dot_product():
    support_x = [[1.0, 0.0], [0.0, 1.0]]
    support_y = [0, 1]
    query_x = [[0.9, 0.1]]
    clf = PairwiseSimilarityClassifier()
    clf.fit(support_x, support_y)
    preds = clf.predict(query_x)
    assert preds == [0]
