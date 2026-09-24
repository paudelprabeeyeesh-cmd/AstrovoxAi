from advanced_backend.scalability_patterns import Partitioner, ReplicaSet, Sharder


def test_sharder_distribution():
    sh = Sharder(num_shards=4)
    counts = {i: 0 for i in range(4)}
    for idx in range(100):
        counts[sh.shard_of({"id": idx})] += 1
    assert sum(counts.values()) == 100


def test_shard_range():
    sh = Sharder(num_shards=4)
    assert len(sh.shard_range(0)) == 2


def test_replica_set_read():
    rs = ReplicaSet(primary="p1", replicas=["r1", "r2"])
    reads = {rs.read() for _ in range(50)}
    assert "p1" in reads


def test_partitioner_hash():
    p = Partitioner(strategy="hash")
    assert 0 <= p.partition("abc", 8) < 8


def test_partitioner_range():
    p = Partitioner(strategy="range")
    assert 0 <= p.partition("a", 8) < 8
