from scalability_patterns.partitioning import Partitioner


def test_partitioner_hash():
    p = Partitioner(strategy="hash")
    assert 0 <= p.partition("abc", 8) < 8


def test_partitioner_range():
    p = Partitioner(strategy="range")
    assert 0 <= p.partition("a", 8) < 8


def test_partitioner_empty_key():
    p = Partitioner(strategy="range")
    assert 0 <= p.partition("", 8) < 8


def test_partitioner_bounds():
    p = Partitioner(strategy="hash")
    low, high = p.bounds(0, 4)
    assert low == 0
    assert high > 0
