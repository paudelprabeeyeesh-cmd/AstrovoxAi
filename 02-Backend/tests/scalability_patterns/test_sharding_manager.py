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


def test_shard_of_custom_key():
    sm = ShardingManager(num_shards=4, shard_key="user_id")
    assert 0 <= sm.shard_of({"user_id": 10}) < 4


def test_shard_of_deterministic():
    sm = ShardingManager(num_shards=8)
    record = {"id": 12345}
    first = sm.shard_of(record)
    second = sm.shard_of(record)
    assert first == second


def test_remove_node_not_present():
    sm = ShardingManager(num_shards=2)
    sm.assign_node(0, "node-a")
    sm.remove_node(0, "node-b")
    assert sm.shard_for_node("node-a") == 0


def test_assign_multiple_nodes():
    sm = ShardingManager(num_shards=2)
    sm.assign_node(0, "node-a")
    sm.assign_node(0, "node-b")
    assert sm.shard_for_node("node-a") == 0
    assert sm.shard_for_node("node-b") == 0


def test_shard_for_node_not_assigned():
    sm = ShardingManager(num_shards=2)
    assert sm.shard_for_node("missing") is None


def test_shard_ranges_distinct():
    sm = ShardingManager(num_shards=4)
    r0 = sm.shard_range(0)
    r1 = sm.shard_range(1)
    assert r0[1] < r1[0]


def test_shard_defaults():
    shard = Shard(id=0, range_start=0, range_end=100)
    assert shard.nodes == []
    assert shard.status == "active"


def test_sharding_manager_defaults():
    sm = ShardingManager()
    assert sm._num_shards == 4
    assert sm._shard_key == "id"
