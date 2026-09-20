import importlib
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)

class TestObservability:
    def test_metrics_endpoint(self):
        r = client.get("/metrics")
        assert r.status_code == 200

    def test_health_check(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_ready_check(self):
        r = client.get("/ready")
        assert r.status_code in (200, 503)

    def test_live_check(self):
        r = client.get("/live")
        assert r.status_code in (200, 503)
