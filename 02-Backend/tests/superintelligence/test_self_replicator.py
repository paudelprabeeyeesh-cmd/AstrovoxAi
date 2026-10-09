import pytest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.self_replicator import (
    SelfReplicator,
    Template,
    Replica,
)


class TestSelfReplicator:
    def test_register_template(self):
        replicator = SelfReplicator(max_generation=3, branch_factor=2, mutation_rate=0.1)
        template = replicator.register_template("core", {"version": 1, "config": {}}, constraints=["c1"])
        assert isinstance(template, Template)
        assert template.name == "core"
        assert len(template.constraints) == 1

    def test_replicate_creates_replica(self):
        replicator = SelfReplicator(max_generation=3, branch_factor=2)
        replicator.register_template("core", {"version": 1})
        replica = replicator.replicate("core", state={"version": 2})
        assert isinstance(replica, Replica)
        assert replica.generation == 0
        assert replica.state["version"] == 2

    def test_replicate_unknown_template_raises(self):
        replicator = SelfReplicator()
        with pytest.raises(ValueError):
            replicator.replicate("unknown")

    def test_spawn_offspring(self):
        replicator = SelfReplicator(max_generation=3, branch_factor=2)
        replicator.register_template("core", {"value": 1})
        parent = replicator.replicate("core")
        children = replicator.spawn_offspring(parent)
        assert len(children) == 2
        assert all(child.generation == 1 for child in children)
        assert len(parent.children) == 2

    def test_max_generation_enforced(self):
        replicator = SelfReplicator(max_generation=1, branch_factor=2)
        replicator.register_template("core", {"value": 1})
        root = replicator.replicate("core")
        replicator.spawn_offspring(root)
        children = replicator.spawn_offspring(root.children[0])
        assert len(children) == 0

    def test_run_replication(self):
        replicator = SelfReplicator(max_generation=2, branch_factor=2)
        replicator.register_template("core", {"value": 1})
        root = replicator.run_replication("core", initial_state={"value": 1})
        assert root.generation == 0
        assert len(replicator.get_registry()) > 1

    def test_count_generations(self):
        replicator = SelfReplicator(max_generation=2, branch_factor=2)
        replicator.register_template("core", {"value": 1})
        replicator.run_replication("core")
        counts = replicator.count_generations()
        assert 0 in counts
        assert counts[0] >= 1

    def test_stats(self):
        replicator = SelfReplicator(max_generation=2, branch_factor=2)
        replicator.register_template("core", {"value": 1})
        replicator.replicate("core")
        stats = replicator.get_stats()
        assert stats["total_replicas"] == 1
        assert stats["templates_registered"] == 1
        assert "generation_counts" in stats

    def test_max_generation_exceeded_raises(self):
        replicator = SelfReplicator(max_generation=1, branch_factor=2)
        replicator.register_template("core", {"value": 1})
        parent = replicator.replicate("core")
        child = replicator.spawn_offspring(parent)[0]
        with pytest.raises(ValueError):
            replicator.replicate("core", parent=child)

    def test_replicate_mutation(self):
        replicator = SelfReplicator(max_generation=3, branch_factor=2, mutation_rate=0.9)
        replicator.register_template("core", {"value": 10})
        parent = replicator.replicate("core", state={"value": 10})
        child = replicator.replicate("core", parent=parent)
        assert child.generation == 1

    def test_spawn_offspring_unknown_template_raises(self):
        replicator = SelfReplicator()
        replicator.register_template("core", {"value": 1})
        parent = replicator.replicate("core")
        with pytest.raises(ValueError):
            replicator.spawn_offspring(parent, template_name="unknown")

    def test_run_replication_stops_on_empty_frontier(self):
        replicator = SelfReplicator(max_generation=2, branch_factor=1)
        replicator.register_template("core", {"value": 1})
        root = replicator.run_replication("core")
        assert root.generation == 0
