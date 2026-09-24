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


def test_partitioner_default_strategy():
    p = Partitioner()
    assert p.strategy == "hash"
    assert 0 <= p.partition("abc", 8) < 8


def test_partitioner_unknown_strategy():
    p = Partitioner(strategy="unknown")
    assert p.partition("abc", 8) == 0


def test_partitioner_hash_deterministic():
    p = Partitioner(strategy="hash")
    assert p.partition("abc", 8) == p.partition("abc", 8)


def test_partitioner_bounds_custom_key_space():
    p = Partitioner(strategy="range")
    low, high = p.bounds(0, 2, key_space=100)
    assert low == 0
    assert high == 49
    low2, high2 = p.bounds(1, 2, key_space=100)
    assert low2 == 50
    assert high2 == 99


def test_partitioner_single_partition():
    p = Partitioner(strategy="hash")
    assert p.partition("abc", 1) == 0
