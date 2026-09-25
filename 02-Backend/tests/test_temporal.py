"""Temporal computing tests.

Tests for:
- Time-travel debugging
- Temporal database with event sourcing, CQRS, and audit trail
- Timeline-based systems with branching and merging
- State management with CRDTs and immutable trees
- Temporal AI with context windows and forecasting
"""

from __future__ import annotations

import datetime
import time

from app.temporal import (
    BreakpointType,
    ConsistencyLevel,
    ConsistencyManager,
    ConversationTimeline,
    CausalChainAnalyzer,
    CausalLink,
    DecisionTree,
    Direction,
    GSet,
    HistoricalPatternRecognizer,
    ImmutableStateTree,
    LWWRegister,
    ORSet,
    PNCounter,
    ScenarioAnalyzer,
    StateDiffer,
    StatePredictor,
    StateSnapshot,
    TemporalAttention,
    TemporalBreakpoint,
    TemporalDatabase,
    TimeAwareContextWindow,
    TimeSeriesForecaster,
    TimeTravelDebugger,
    TimelineExporter,
    TimelineNode,
    get_debugger,
)


class TestTimeTravelDebugger:
    def setup_method(self):
        self.debugger = get_debugger("test")

    def test_capture_and_restore_snapshot(self):
        state = {"step": 1, "value": 42}
        snap = self.debugger.capture_snapshot(state, label="init")
        assert snap.state == state
        restored = self.debugger.restore_snapshot(snap.snapshot_id)
        assert restored["step"] == 1

    def test_branch_creation_and_switch(self):
        branch = self.debugger.create_branch("experiment", created_by="test")
        assert branch in self.debugger.list_branches()
        self.debugger.switch_branch(branch)
        assert self.debugger.get_current_branch() == branch

    def test_breakpoint_lifecycle(self):
        bp = TemporalBreakpoint(
            breakpoint_id="bp-1",
            breakpoint_type=BreakpointType.POSITION,
            target=10,
            description="stop at 10",
        )
        self.debugger.set_breakpoint(bp)
        bps = self.debugger.list_breakpoints()
        assert len(bps) == 1
        assert bps[0]["breakpoint_id"] == "bp-1"
        self.debugger.remove_breakpoint("bp-1")
        assert len(self.debugger.list_breakpoints()) == 0

    def test_step_forward_and_backward(self):
        self.debugger.capture_snapshot({"x": 0}, label="start")
        evt = type("E", (), {"event_id": "e1", "timestamp": datetime.datetime.now(datetime.timezone.utc), "position": 1, "event_type": "tick", "payload": {}, "branch_id": "main"})()
        state = self.debugger.step_forward(evt, lambda s, e: {"x": s.get("x", 0) + 1})
        assert state["x"] == 1
        self.debugger.step_backward(1)
        assert self.debugger.get_current_position() == 0

    def test_state_comparison(self):
        snap_a = self.debugger.capture_snapshot({"a": 1}, label="a")
        snap_b = self.debugger.capture_snapshot({"a": 2, "b": 3}, label="b")
        diff = self.debugger.compare_snapshots(snap_a.snapshot_id, snap_b.snapshot_id)
        assert diff["summary"]["changed_count"] == 1
        assert diff["summary"]["added_count"] == 1

    def test_point_in_time_query(self):
        self.debugger.capture_snapshot({"v": 1}, label="v1")
        t = datetime.datetime.now(datetime.timezone.utc)
        self.debugger.capture_snapshot({"v": 2}, label="v2")
        state = self.debugger.query_at_time(t)
        assert state is not None


class TestTemporalDatabase:
    def setup_method(self):
        self.db = TemporalDatabase(consistency=ConsistencyLevel.EVENTUAL)

    def test_apply_and_query(self):
        entity = self.db.apply("e1", "create", {"name": "test"}, actor="u1")
        assert entity.version == 1
        state = self.db.query("e1")
        assert state["name"] == "test"

    def test_point_in_time(self):
        self.db.apply("e1", "create", {"v": 1}, actor="u1")
        t = datetime.datetime.now(datetime.timezone.utc)
        time.sleep(0.01)
        self.db.apply("e1", "update", {"v": 2}, actor="u1")
        state = self.db.query("e1", as_of=t)
        assert state["v"] == 1

    def test_history(self):
        self.db.apply("e1", "create", {"v": 1}, actor="u1")
        self.db.apply("e1", "update", {"v": 2}, actor="u1")
        history = self.db.history("e1")
        assert len(history) == 2

    def test_audit_trail(self):
        self.db.apply("e1", "create", {"v": 1}, actor="u1")
        trail = self.db.audit_trail("e1")
        assert len(trail) >= 1
        assert trail[0]["operation"] == "create"

    def test_lineage(self):
        self.db.apply("e1", "create", {"v": 1}, actor="u1")
        lineage = self.db.lineage("e1")
        assert len(lineage) >= 1

    def test_verify_audit_integrity(self):
        self.db.apply("e1", "create", {"v": 1}, actor="u1")
        assert self.db.verify_audit_integrity() is True

    def test_constraint_violation(self):
        self.db._constraints.register(
            type("C", (), {"constraint_id": "c1", "entity_type": "entity", "rule": "x>0", "validator": lambda ns, _: ns.get("x", 0) > 0, "enabled": True, "description": ""})()
        )
        import pytest
        with pytest.raises(ValueError):
            self.db.apply("e1", "create", {"x": -1}, actor="u1", entity_type="entity")


class TestTimeline:
    def setup_method(self):
        self.timeline = ConversationTimeline("conv-1")

    def test_add_message(self):
        node = self.timeline.add_message("user", "hello")
        assert node.content["role"] == "user"

    def test_branch_and_merge(self):
        node = self.timeline.add_message("user", "hello")
        branch = self.timeline.branch("alt", node.node_id)
        self.timeline.add_message("assistant", "hi", branch_id=branch)
        merged = self.timeline.merge(branch, "main", node.node_id)
        assert merged.node_type == "merge"

    def test_divergence_detection(self):
        n1 = self.timeline.add_message("user", "hello")
        branch = self.timeline.branch("alt", n1.node_id)
        self.timeline.add_message("assistant", "hi", branch_id=branch)
        divergence = self.timeline.detect_divergence("main", branch)
        assert divergence is not None

    def test_visualize(self):
        self.timeline.add_message("user", "hello")
        viz = self.timeline.visualize()
        assert "nodes" in viz
        assert len(viz["nodes"]) >= 1

    def test_path_to_root(self):
        node = self.timeline.add_message("user", "hello")
        path = self.timeline.get_path_to_root(node.node_id)
        assert len(path) >= 1

    def test_decision_tree(self):
        tree = DecisionTree("tree-1")
        root = tree.add_decision(None, {"question": "go?"})
        outcome = tree.add_outcome(root.node_id, {"result": "yes"})
        viz = tree.visualize()
        assert viz["node_count"] >= 2

    def test_scenario_analysis(self):
        analyzer = ScenarioAnalyzer(self.timeline)
        result = analyzer.simulate("s1", "main", lambda nodes: {"score": 0.5})
        assert result.scenario_id == "s1"

    def test_causal_chain(self):
        n1 = self.timeline.add_message("user", "hello")
        n2 = self.timeline.add_message("assistant", "hi")
        analyzer = CausalChainAnalyzer(self.timeline)
        analyzer.add_link(n1.node_id, n2.node_id, "causes")
        chain = analyzer.analyze(n1.node_id)
        assert chain["start_node_id"] == n1.node_id

    def test_export_json(self):
        self.timeline.add_message("user", "hello")
        exporter = TimelineExporter(self.timeline)
        json_data = exporter.to_json()
        assert "hello" in json_data

    def test_export_csv(self):
        self.timeline.add_message("user", "hello")
        exporter = TimelineExporter(self.timeline)
        csv_data = exporter.to_csv()
        assert "hello" in csv_data


class TestStateManager:
    def setup_method(self):
        self.tree = ImmutableStateTree()

    def test_commit_and_get(self):
        state = self.tree.commit("default", {"x": 1})
        assert self.tree.get("default")["x"] == 1

    def test_history(self):
        self.tree.commit("default", {"x": 1})
        self.tree.commit("default", {"x": 2})
        hist = self.tree.history("default")
        assert len(hist) == 2

    def test_rollback(self):
        self.tree.commit("default", {"x": 1})
        self.tree.commit("default", {"x": 2})
        self.tree.rollback("default", steps=1)
        assert self.tree.get("default")["x"] == 1

    def test_diff(self):
        self.tree.commit("default", {"x": 1})
        id_a = self.tree._latest["default"]
        self.tree.commit("default", {"x": 2})
        id_b = self.tree._latest["default"]
        diff = self.tree.diff("default", id_a, id_b)
        assert diff["summary"]["changed_count"] == 1

    def test_optimize(self):
        self.tree.commit("default", {"x": 1})
        result = self.tree.optimize("default")
        assert result["optimized"] is True

    def test_state_differ(self):
        diff = StateDiffer.diff({"a": 1}, {"a": 2, "b": 3})
        assert diff["summary"]["changed_count"] == 1
        assert diff["summary"]["added_count"] == 1

    def test_state_predictor(self):
        pred = StatePredictor()
        pred.observe({"a": 1}, {"a": 2}, 1.0)
        predictions = pred.predict({"a": 1}, steps=1)
        assert len(predictions) == 1

    def test_crdt_gset(self):
        gset = GSet()
        gset.add("a")
        gset.add("b")
        assert gset.has("a")
        assert not gset.has("c")

    def test_crdt_pncounter(self):
        counter = PNCounter()
        counter.increment()
        counter.decrement()
        assert counter.value() == 0

    def test_crdt_lww(self):
        reg = LWWRegister("n1")
        reg.set("hello")
        assert reg.get() == "hello"

    def test_crdt_orset(self):
        orset = ORSet()
        orset.add("a")
        assert orset.has("a")
        orset.remove("a")
        assert not orset.has("a")

    def test_consistency_manager(self):
        mgr = ConsistencyManager(consistency_level="eventual")
        mgr.propose({"k": "v"})
        assert len(mgr.get_pending()) == 0


class TestTemporalAI:
    def test_context_window(self):
        cw = TimeAwareContextWindow(max_tokens=10, decay_half_life_s=3600.0)
        cw.add("hello")
        cw.add("world")
        text = cw.context_text()
        assert "hello" in text

    def test_temporal_attention(self):
        attn = TemporalAttention()
        query = {"timestamp": datetime.datetime.now(datetime.timezone.utc), "text": "q"}
        keys = [{"text": "a"}, {"text": "b"}]
        ts = [datetime.datetime.now(datetime.timezone.utc), datetime.datetime.now(datetime.timezone.utc)]
        results = attn.attend(query, keys, ts)
        assert len(results) == 2

    def test_pattern_recognizer(self):
        pr = HistoricalPatternRecognizer()
        pr.observe(["a", "b", "c"])
        pr.observe(["a", "b", "c"])
        patterns = pr.detect_patterns()
        assert len(patterns) >= 1

    def test_time_series_forecaster(self):
        f = TimeSeriesForecaster()
        now = datetime.datetime.now(datetime.timezone.utc)
        f.observe("s1", now, 1.0)
        f.observe("s1", datetime.datetime.fromtimestamp(now.timestamp() + 60, tz=datetime.timezone.utc), 2.0)
        forecast = f.forecast("s1", horizon=2)
        assert len(forecast) == 2
