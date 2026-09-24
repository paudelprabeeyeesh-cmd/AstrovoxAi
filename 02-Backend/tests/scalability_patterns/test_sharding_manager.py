from scalability_patterns.sharding_manager import Shard, ShardingManager


def test_shard_distribution():
    sm = ShardingManager(num_shards=4)
    counts = {i: 0 for i in range(4)}
    for idx in range(100):
        counts[sm.shard_of({"id": idx})] += 1
    assert sum(counts.values()) == 100


def test_shard_range():
    sm = ShardingManager(num_shards=4)
    low, high = sm.shard_range(0)
    assert low == 0
    assert high > 0


def test_assign_and_find_node():
    sm = ShardingManager(num_shards=2)
    sm.assign_node(0, "node-a")
    assert sm.shard_for_node("node-a") == 0
    sm.remove_node(0, "node-a")
    assert sm.shard_for_node("node-a") is None


def test_get_shard():
    sm = ShardingManager(num_shards=4)
    shard = sm.get_shard(1)
    assert isinstance(shard, Shard)
    assert shard.id == 1


def test_all_shards_count():
    sm = ShardingManager(num_shards=3)
    assert len(sm.all_shards()) == 3
