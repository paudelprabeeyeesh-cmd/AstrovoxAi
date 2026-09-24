
import os
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.e2e


class TestEndToEndUserFlows:
    def test_health_endpoint(self):
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

    def test_metrics_endpoint(self):
        with TestClient(app) as client:
            response = client.get("/metrics")
            assert response.status_code == 200

    def test_analytics_dashboard_requires_auth(self):
        with TestClient(app) as client:
            response = client.get("/analytics/dashboard")
            assert response.status_code in (401, 403, 302)
