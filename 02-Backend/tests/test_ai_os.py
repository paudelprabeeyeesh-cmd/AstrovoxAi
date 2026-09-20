import importlib
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)


class TestAIOS:
    def test_healthz(self):
        r = client.get("/healthz")
        assert r.status_code in (200, 503)

    def test_version(self):
        r = client.get("/version")
        assert r.status_code == 200

    def test_terms_page(self):
        r = client.get("/terms")
        assert r.status_code == 200
