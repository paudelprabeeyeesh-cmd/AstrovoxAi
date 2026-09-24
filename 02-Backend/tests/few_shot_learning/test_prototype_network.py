import pytest
from few_shot_learning.prototype_network import PrototypeNetwork
from few_shot_learning.episode_sampler import Episode


def _make_episode():
    support_x = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
    support_y = [0, 0, 0]
    query_x = [[0.5, 0.0], [0.0, 0.5]]
    query_y = [0, 0]
    return Episode(
        support_x=support_x,
        support_y=support_y,
        query_x=query_x,
        query_y=query_y,
        n_way=1,
        k_shot=3,
        query_size=2,
    )


def test_train_episode_returns_accuracy():
    net = PrototypeNetwork(embedding_dim=2, distance_metric="euclidean")
    episode = _make_episode()
    result = net.train_episode(episode)
    assert "accuracy" in result
    assert "n_query" in result
    assert result["n_query"] == 2
    assert len(net.loss_history) == 1


def test_evaluate_episode():
    net = PrototypeNetwork(embedding_dim=2, distance_metric="euclidean")
    episode = _make_episode()
    result = net.evaluate_episode(episode)
    assert "accuracy" in result
    assert "predictions" in result
    assert len(result["predictions"]) == 2


def test_classify_with_prototypes():
    net = PrototypeNetwork(embedding_dim=2, distance_metric="euclidean")
    support_x = [[0.0, 0.0], [10.0, 10.0]]
    support_y = [0, 1]
    prototypes = net.compute_prototypes(support_x, support_y)
    query_x = [[0.5, 0.5], [9.5, 9.5]]
    preds = net.classify(query_x, prototypes)
    assert preds == [0, 1]


def test_classify_cosine():
    net = PrototypeNetwork(embedding_dim=2, distance_metric="cosine")
    support_x = [[1.0, 0.0], [0.0, 1.0]]
    support_y = [0, 1]
    prototypes = net.compute_prototypes(support_x, support_y)
    query_x = [[0.9, 0.1], [0.1, 0.9]]
    preds = net.classify(query_x, prototypes)
    assert preds == [0, 1]


def test_classify_empty_prototypes():
    net = PrototypeNetwork(embedding_dim=2)
    preds = net.classify([[1.0, 2.0]])
    assert preds == [0]


def test_compute_prototypes():
    net = PrototypeNetwork(embedding_dim=2, distance_metric="euclidean")
    support_x = [[0.0, 0.0], [2.0, 2.0]]
    support_y = [0, 0]
    prototypes = net.compute_prototypes(support_x, support_y)
    assert 0 in prototypes
    assert len(prototypes[0]) == 2


def test_get_prototype_distances():
    net = PrototypeNetwork(embedding_dim=2, distance_metric="euclidean")
    support_x = [[0.0, 0.0], [10.0, 10.0]]
    support_y = [0, 1]
    net.compute_prototypes(support_x, support_y)
    dists = net.get_prototype_distances([[0.5, 0.5]])
    assert 0 in dists
    assert 1 in dists
    assert len(dists[0]) == 1
    assert len(dists[1]) == 1
    assert dists[0][0] < dists[1][0]


def test_unknown_distance_metric_raises():
    net = PrototypeNetwork(embedding_dim=2, distance_metric="invalid")
    with pytest.raises(ValueError):
        net.classify([[1.0, 2.0]])
