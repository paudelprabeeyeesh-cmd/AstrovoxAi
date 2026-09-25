"""Temporal time manipulation tests."""

from __future__ import annotations

import pytest

from app.temporal.snapshots import SnapshotEngine, SnapshotStrategy
from app.temporal.cqrs import CommandBus, QueryBus, Command, Event, Query, CQRS
from app.temporal.reverse_debugger import ReverseDebugger, DebugDirection
from app.temporal.branching import BranchTimelineManager, BranchType, BranchStatus
from app.temporal.causal import CausalChainAnalyzer, CausalEvent, CausalEdge
from app.temporal.diffing import StateDiffer, HistoricalDiff
from app.temporal.rollback import RollbackAutomation, RollbackTrigger


class TestSnapshotEngine:
    def test_create_snapshot(self):
        engine = SnapshotEngine()
        snapshot = engine.create_snapshot("agg1", "TestAggregate", 1, {"key": "value"}, 1)
        assert snapshot.aggregate_id == "agg1"
        assert snapshot.state["key"] == "value"
        assert snapshot.version == 1

    def test_get_latest_snapshot(self):
        engine = SnapshotEngine()
        engine.create_snapshot("agg1", "TestAggregate", 1, {"key": "value1"}, 1)
        engine.create_snapshot("agg1", "TestAggregate", 2, {"key": "value2"}, 2)
        latest = engine.get_latest_snapshot("agg1")
        assert latest.version == 2

    def test_get_snapshot_at_version(self):
        engine = SnapshotEngine()
        engine.create_snapshot("agg1", "TestAggregate", 1, {"key": "value1"}, 1)
        engine.create_snapshot("agg1", "TestAggregate", 3, {"key": "value3"}, 3)
        snap = engine.get_snapshot_at("agg1", 2)
        assert snap.version == 1

    def test_compact_snapshots(self):
        engine = SnapshotEngine()
        for i in range(1, 6):
            engine.create_snapshot("agg1", "TestAggregate", i, {"key": f"value{i}"}, i)
        engine.compact("agg1", keep_n=2)
        assert len(engine.get_snapshots("agg1")) == 2

    def test_should_create_snapshot(self):
        engine = SnapshotEngine(strategy=SnapshotStrategy.EVERY_N_EVENTS, every_n_events=3)
        engine.record_event("agg1")
        engine.record_event("agg1")
        engine.record_event("agg1")
        assert engine.should_create_snapshot("agg1", 3)


class TestCommandBus:
    def test_register_handler(self):
        bus = CommandBus()
        def handler(cmd):
            return [Event(event_type="test", aggregate_id="agg1", version=1)]
        bus.register("test_command", handler)
        assert "test_command" in bus._handlers

    def test_dispatch(self):
        import asyncio
        bus = CommandBus()
        def handler(cmd):
            return [Event(event_type="test", aggregate_id="agg1", version=1)]
        bus.register("test_command", handler)
        cmd = Command(command_type="test_command")
        result = asyncio.run(bus.dispatch(cmd))
        assert len(result) == 1

    def test_dispatch_no_handler(self):
        import asyncio
        bus = CommandBus()
        cmd = Command(command_type="nonexistent")
        with pytest.raises(Exception):
            asyncio.run(bus.dispatch(cmd))


class TestQueryBus:
    def test_register_handler(self):
        bus = QueryBus()
        def handler(qry):
            return QueryResult(query_id=qry.query_id, result="test")
        bus.register("test_query", handler)
        assert "test_query" in bus._handlers

    def test_execute_query(self):
        import asyncio
        bus = QueryBus()
        def handler(qry):
            return QueryResult(query_id=qry.query_id, result="test")
        bus.register("test_query", handler)
        qry = Query(query_type="test_query")
        result = asyncio.run(bus.execute(qry))
        assert result.result == "test"


class TestCausalChainAnalyzer:
    def test_add_events(self):
        analyzer = CausalChainAnalyzer()
        event = CausalEvent(event_id="e1", event_type="test", aggregate_id="a1", version=1, occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        analyzer.add_event(event)
        assert "e1" in analyzer._events

    def test_add_edge(self):
        analyzer = CausalChainAnalyzer()
        event1 = CausalEvent(event_id="e1", event_type="test", aggregate_id="a1", version=1, occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        event2 = CausalEvent(event_id="e2", event_type="test", aggregate_id="a1", version=2, occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        analyzer.add_events([event1, event2])
        edge = CausalEdge(edge_id="ed1", source_event_id="e1", target_event_id="e2", edge_type=CausalEdgeType.CAUSED)
        analyzer.add_edge(edge)
        assert "ed1" in analyzer._edges

    def test_build_chain(self):
        analyzer = CausalChainAnalyzer()
        event1 = CausalEvent(event_id="e1", event_type="test", aggregate_id="a1", version=1, occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        event2 = CausalEvent(event_id="e2", event_type="test", aggregate_id="a1", version=2, occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        analyzer.add_events([event1, event2])
        chain = analyzer.build_chain("c1", "Test Chain", ["e1", "e2"])
        assert chain.chain_id == "c1"
        assert len(chain.events) == 2


class TestStateDiffer:
    def test_diff(self):
        differ = StateDiffer()
        state_a = {"key1": "value1", "key2": "value2"}
        state_b = {"key1": "value1_modified", "key3": "value3"}
        diff = differ.diff(state_a, state_b)
        assert len(diff._compute_field_diff()["additions"]) == 1
        assert len(diff._compute_field_diff()["deletions"]) == 0
        assert len(diff._compute_field_diff()["modifications"]) == 1

    def test_diff_sequence(self):
        differ = StateDiffer()
        states = [
            {"key": "value1"},
            {"key": "value2"},
            {"key": "value3"},
        ]
        diffs = differ.diff_sequence(states)
        assert len(diffs) == 2


class TestBranchTimelineManager:
    def test_create_branch(self):
        manager = BranchTimelineManager()
        branch = manager.create_branch("test_branch", BranchType.TIMELINE, "snap1", 1)
        assert branch.name == "test_branch"
        assert branch.branch_type == BranchType.TIMELINE

    def test_append_snapshot(self):
        manager = BranchTimelineManager()
        branch = manager.create_branch("test_branch", BranchType.TIMELINE, "snap1", 1)
        class FakeSnapshot:
            version = 1
            snapshot_id = "s1"
            created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        manager.append_snapshot(branch.branch_id, FakeSnapshot())
        assert len(manager._branches[branch.branch_id].snapshots) == 1

    def test_get_visualization(self):
        manager = BranchTimelineManager()
        manager.create_branch("test_branch", BranchType.TIMELINE, "snap1", 1)
        viz = manager.get_visualization()
        assert len(viz["nodes"]) == 1


class TestRollbackAutomation:
    def test_create_plan(self):
        automation = RollbackAutomation(None, None, None)
        plan = automation.create_plan("agg1", 5)
        assert plan.aggregate_id == "agg1"
        assert plan.target_version == 5

    def test_execute_rollback(self):
        automation = RollbackAutomation(None, None, None)
        plan = automation.create_plan("agg1", 5)
        result = automation.execute(plan.plan_id)
        assert result.status.value == "completed"
