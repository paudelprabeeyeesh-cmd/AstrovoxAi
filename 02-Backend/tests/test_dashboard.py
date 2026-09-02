"""Tests for dashboard API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def authorized_headers():
    return {"Authorization": "Bearer test-token"}


class TestDashboardRoutes:
    def test_get_stats(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/dashboard/stats", headers=authorized_headers())
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "OK"
            assert "stats" in data

    def test_get_tasks(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/dashboard/tasks", headers=authorized_headers())
            assert resp.status_code == 200

    def test_get_workflows(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/dashboard/workflows", headers=authorized_headers())
            assert resp.status_code == 200

    def test_get_agents(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/dashboard/agents", headers=authorized_headers())
            assert resp.status_code == 200

    def test_get_tools(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/dashboard/tools", headers=authorized_headers())
            assert resp.status_code == 200

    def test_get_logs(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/dashboard/logs", headers=authorized_headers())
            assert resp.status_code == 200

    def test_get_timeline(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/dashboard/timeline", headers=authorized_headers())
            assert resp.status_code == 200

    def test_get_metrics(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/dashboard/metrics", headers=authorized_headers())
            assert resp.status_code == 200
