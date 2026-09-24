import pytest
from few_shot_learning.episode_sampler import Episode, EpisodeSampler


def _make_data():
    x = [[float(i), float(i + 1)] for i in range(20)]
    y = [i % 3 for i in range(20)]
    return x, y


def test_sample_episode_basic():
    x, y = _make_data()
    sampler = EpisodeSampler(seed=0)
    episode = sampler.sample_episode(x, y, n_way=2, k_shot=2, query_size=2)
    assert episode.n_way == 2
    assert episode.k_shot == 2
    assert episode.query_size == 2
    assert len(episode.support_x) == 4
    assert len(episode.support_y) == 4
    assert len(episode.query_x) == 4
    assert len(episode.query_y) == 4
    assert set(episode.support_y) == {0, 1}
    assert set(episode.query_y) == {0, 1}


def test_sample_episode_raises_on_too_many_ways():
    x, y = _make_data()
    sampler = EpisodeSampler(seed=0)
    with pytest.raises(ValueError):
        sampler.sample_episode(x, y, n_way=10, k_shot=1, query_size=1)


def test_sample_episode_raises_on_insufficient_samples():
    x = [[0.0, 1.0], [2.0, 3.0]]
    y = [0, 1]
    sampler = EpisodeSampler(seed=0)
    with pytest.raises(ValueError):
        sampler.sample_episode(x, y, n_way=2, k_shot=2, query_size=2)


def test_sample_batch():
    x, y = _make_data()
    sampler = EpisodeSampler(seed=0)
    batch = sampler.sample_batch(x, y, n_way=2, k_shot=1, query_size=1, batch_size=3)
    assert len(batch) == 3
    for ep in batch:
        assert len(ep.support_x) == 2
        assert len(ep.query_x) == 2


def test_stratified_split():
    x, y = _make_data()
    sampler = EpisodeSampler(seed=0)
    s_x, s_y, q_x, q_y = sampler.stratified_split(x, y, support_ratio=0.5)
    assert len(s_x) == len(s_y)
    assert len(q_x) == len(q_y)
    assert len(s_x) + len(q_x) == len(x)
    assert sorted(set(s_y) | set(q_y)) == sorted(set(y))


def test_episode_dataclass():
    ep = Episode(
        support_x=[[1.0, 2.0]],
        support_y=[0],
        query_x=[[3.0, 4.0]],
        query_y=[0],
        n_way=1,
        k_shot=1,
        query_size=1,
    )
    assert ep.n_way == 1
    assert ep.k_shot == 1
    assert ep.query_size == 1
