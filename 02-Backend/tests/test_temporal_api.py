"""Temporal API endpoint tests."""

from __future__ import annotations

import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers.temporal_route import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)


class TestTemporalHealth:
    def test_health(self):
        resp = client.get("/temporal/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestTimeTravelAPI:
    def test_capture_snapshot(self):
        resp = client.post("/temporal/debug/capture-snapshot", json={"state": {"x": 1}, "label": "init"})
        assert resp.status_code == 200
        assert "snapshot" in resp.json()

    def test_list_snapshots(self):
        resp = client.get("/temporal/debug/snapshots")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_switch_branch(self):
        resp = client.post("/temporal/debug/branch", json={"name": "exp", "created_by": "test"})
        assert resp.status_code == 200
        branch_id = resp.json()["branch_id"]
        resp = client.post("/temporal/debug/switch-branch", json={"branch_id": branch_id})
        assert resp.status_code == 200

    def test_breakpoint_lifecycle(self):
        resp = client.post("/temporal/debug/breakpoint", json={"breakpoint_id": "bp1", "breakpoint_type": "position", "target": 10})
        assert resp.status_code == 200
        resp = client.get("/temporal/debug/breakpoints")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        resp = client.delete("/temporal/debug/breakpoint/bp1")
        assert resp.status_code == 200

    def test_step_forward_and_backward(self):
        resp = client.post("/temporal/debug/step-forward", json={"position": 1, "event_type": "tick"})
        assert resp.status_code == 200
        resp = client.post("/temporal/debug/step-backward", json={"steps": 1})
        assert resp.status_code == 200

    def test_compare_snapshots(self):
        resp = client.post("/temporal/debug/capture-snapshot", json={"state": {"a": 1}, "label": "a"})
        snap_a = resp.json()["snapshot"]["snapshot_id"]
        resp = client.post("/temporal/debug/capture-snapshot", json={"state": {"a": 2}, "label": "b"})
        snap_b = resp.json()["snapshot"]["snapshot_id"]
        resp = client.get("/temporal/debug/compare", params={"snapshot_id_a": snap_a, "snapshot_id_b": snap_b})
        assert resp.status_code == 200
        assert "diff" in resp.json()

    def test_visualize_branch(self):
        resp = client.get("/temporal/debug/visualize-branch", params={"branch_id": "main"})
        assert resp.status_code == 200
        assert "nodes" in resp.json()


class TestTemporalDatabaseAPI:
    def test_apply_and_query(self):
        resp = client.post("/temporal/db/apply", json={"entity_id": "e1", "operation": "create", "data": {"name": "test"}, "actor": "u1"})
        assert resp.status_code == 200
        resp = client.get("/temporal/db/query", params={"entity_id": "e1"})
        assert resp.status_code == 200
        assert resp.json()["state"]["name"] == "test"

    def test_history(self):
        client.post("/temporal/db/apply", json={"entity_id": "e2", "operation": "create", "data": {"v": 1}, "actor": "u1"})
        resp = client.get("/temporal/db/history", params={"entity_id": "e2"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_audit_trail(self):
        resp = client.get("/temporal/db/audit", params={"entity_id": "e1"})
        assert resp.status_code == 200

    def test_verify_audit(self):
        resp = client.get("/temporal/db/verify-audit")
        assert resp.status_code == 200
        assert resp.json()["valid"] is True


class TestTimelineAPI:
    def test_create_and_add_message(self):
        client.post("/temporal/timeline/create", json="conv-1")
        resp = client.post("/temporal/timeline/add-message", json={"conversation_id": "conv-1", "role": "user", "content": "hello"})
        assert resp.status_code == 200
        assert resp.json()["node"]["content"]["role"] == "user"

    def test_visualize_timeline(self):
        resp = client.get("/temporal/timeline/visualize", params={"conversation_id": "conv-1"})
        assert resp.status_code == 200
        assert "nodes" in resp.json()

    def test_branch_and_merge(self):
        resp = client.post("/temporal/timeline/add-message", json={"conversation_id": "conv-2", "role": "user", "content": "hi"})
        node_id = resp.json()["node"]["node_id"]
        resp = client.post("/temporal/timeline/branch", json={"conversation_id": "conv-2", "name": "alt", "from_node_id": node_id})
        assert resp.status_code == 200
        branch_id = resp.json()["branch_id"]
        resp = client.post("/temporal/timeline/add-message", json={"conversation_id": "conv-2", "role": "assistant", "content": "hello", "branch_id": branch_id})
        assert resp.status_code == 200


class TestStateManagementAPI:
    def test_commit_and_get(self):
        resp = client.post("/temporal/state/commit", json={"path": "default", "data": {"x": 1}})
        assert resp.status_code == 200
        resp = client.get("/temporal/state/get", params={"path": "default"})
        assert resp.status_code == 200
        assert resp.json()["state"]["x"] == 1

    def test_history(self):
        resp = client.get("/temporal/state/history", params={"path": "default"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_diff(self):
        resp_a = client.post("/temporal/state/commit", json={"path": "default", "data": {"a": 1}})
        state_a = resp_a.json()["state"]["state_id"]
        resp_b = client.post("/temporal/state/commit", json={"path": "default", "data": {"a": 2}})
        state_b = resp_b.json()["state"]["state_id"]
        resp = client.post("/temporal/state/diff", json={"state_id_a": state_a, "state_id_b": state_b, "path": "default"})
        assert resp.status_code == 200
        assert "diff" in resp.json()

    def test_stats(self):
        resp = client.get("/temporal/state/stats")
        assert resp.status_code == 200
        assert "total_states" in resp.json()


class TestTemporalAIAPI:
    def test_context_window(self):
        resp = client.post("/temporal/ai/context/add", json={"text": "hello"})
        assert resp.status_code == 200
        resp = client.get("/temporal/ai/context")
        assert resp.status_code == 200
        assert "context" in resp.json()

    def test_temporal_attention(self):
        resp = client.post("/temporal/ai/attention", json={"query": {"text": "q"}, "keys": [{"text": "a"}], "timestamps": [datetime.datetime.now(datetime.timezone.utc).isoformat()]})
        assert resp.status_code == 200
        assert "attended" in resp.json()

    def test_pattern_detection(self):
        resp = client.post("/temporal/ai/patterns/detect", json=[["a", "b", "c"], ["a", "b", "c"]])
        assert resp.status_code == 200
        assert "patterns" in resp.json()

    def test_forecast(self):
        resp = client.post("/temporal/ai/forecast", json={"series_id": "s1", "horizon": 2})
        assert resp.status_code == 200
        assert "forecast" in resp.json()


class TestTemporalStats:
    def test_stats(self):
        resp = client.get("/temporal/stats")
        assert resp.status_code == 200
        assert "debugger" in resp.json()


class TestBatchOperations:
    def test_batch_apply(self):
        resp = client.post("/temporal/batch/apply", json=[
            {"entity_id": "b1", "operation": "create", "data": {"x": 1}, "actor": "u1"},
            {"entity_id": "b2", "operation": "create", "data": {"x": 2}, "actor": "u1"},
        ])
        assert resp.status_code == 200
        body = resp.json()
        assert body["success_count"] == 2
        assert body["failure_count"] == 0
        assert "batch_id" in body

    def test_batch_query(self):
        client.post("/temporal/batch/apply", json=[{"entity_id": "bq1", "operation": "create", "data": {"y": 1}, "actor": "u1"}])
        resp = client.post("/temporal/batch/query", json=[
            {"entity_id": "bq1"},
        ])
        assert resp.status_code == 200
        body = resp.json()
        assert body["success_count"] == 1

    def test_engine_stats(self):
        resp = client.get("/temporal/engine/stats")
        assert resp.status_code == 200
        assert "debugger" in resp.json()
