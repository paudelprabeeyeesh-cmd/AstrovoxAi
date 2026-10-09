"""Tests for the AI orchestration router."""

from __future__ import annotations

import importlib
import uuid

import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)

from app.auth import get_current_user  # noqa: E402


def _mock_user():
    return {"user_id": "42", "email": "test@test.com"}


@pytest.fixture(autouse=True)
def _mock_auth():
    app = importlib.import_module("app.main").app
    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


class TestRoutingEndpoints:
    def test_route_returns_result(self):
        payload = {
            "task_type": "general_chat",
            "policy": "balanced",
            "fallback_strategy": "cross_provider",
        }
        r = client.post("/ai/routing/route", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert "request_id" in body
        assert "routing" in body
        assert body["routing"]["model_id"]
        assert body["routing"]["provider_name"]

    def test_route_preferred_model(self):
        payload = {
            "preferred_model": "gpt-4",
            "policy": "strict",
            "fallback_strategy": "none",
        }
        r = client.post("/ai/routing/route", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["routing"]["model_id"] == "gpt-4"

    def test_list_routing_models(self):
        r = client.get("/ai/routing/models")
        assert r.status_code == 200
        body = r.json()
        assert "models" in body
        assert len(body["models"]) > 0


class TestTraceEndpoints:
    def test_start_and_get_trace(self):
        r = client.post("/ai/traces?user_message=hello")
        assert r.status_code == 200
        request_id = r.json()["request_id"]

        r = client.get(f"/ai/traces/{request_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["request_id"] == request_id

    def test_add_reasoning_step(self):
        r = client.post("/ai/traces?user_message=hello")
        request_id = r.json()["request_id"]

        payload = {
            "step": "plan",
            "thought": "think step",
            "evidence": ["a"],
            "confidence": 0.9,
        }
        r = client.post(f"/ai/traces/{request_id}/reasoning-step", json=payload)
        assert r.status_code == 200

    def test_complete_trace(self):
        r = client.post("/ai/traces?user_message=hello")
        request_id = r.json()["request_id"]

        r = client.post(f"/ai/traces/{request_id}/complete", json={"final_response": "done"})
        assert r.status_code == 200

    def test_get_trace_not_found(self):
        r = client.get("/ai/traces/nonexistent")
        assert r.status_code == 404


class TestCompressionEndpoints:
    def test_compress_context(self):
        payload = {
            "context": "Python is great. The sky is blue. Code is fun. " * 100,
            "max_tokens": 200,
            "strategy": "hybrid",
        }
        r = client.post("/ai/compression/compress", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["compressed_tokens"] <= payload["max_tokens"]
        assert "request_id" in body

    def test_compress_skips_small(self):
        payload = {"context": "short", "max_tokens": 1000}
        r = client.post("/ai/compression/compress", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["metadata"].get("skipped") is True

    def test_extract_important(self):
        payload = {"context": "Python is great. The sky is blue. Code is fun.", "query": "python code"}
        r = client.post("/ai/compression/extract", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert "extracted" in body

    def test_estimate_tokens(self):
        r = client.get("/ai/compression/estimate-tokens?text=hello+world")
        assert r.status_code == 200
        body = r.json()
        assert body["estimated_tokens"] >= 1


class TestSelfCorrectionEndpoints:
    def test_review_no_issues(self):
        payload = {"response": "short response"}
        r = client.post("/ai/self-correction/review", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["confidence"] == 1.0
        assert body["issues"] == []

    def test_review_empty_response(self):
        payload = {"response": ""}
        r = client.post("/ai/self-correction/review", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["corrected"] == "I couldn't generate a response. Please try again."

    def test_review_too_long(self):
        payload = {"response": "x" * 5000}
        r = client.post("/ai/self-correction/review", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert "too_long" in body["issues"]
        assert body["corrected"].endswith("...")
