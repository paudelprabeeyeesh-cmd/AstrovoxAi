"""Tests for API v1 endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers():
    return {"Authorization": "Bearer test-token"}


class TestAgentManagementAPI:
    def test_list_agents(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/agents", headers=auth_headers())
            assert resp.status_code == 200

    def test_get_agent(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/agents/planner", headers=auth_headers())
            assert resp.status_code == 200

    def test_get_agent_health(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/agents/planner/health", headers=auth_headers())
            assert resp.status_code == 200


class TestWorkflowAPI:
    def test_create_workflow(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.post("/api/v1/workflows", json={
                "name": "Test Workflow",
                "description": "A test",
                "steps": [{"name": "Step1", "action": "agent_task"}],
            }, headers=auth_headers())
            assert resp.status_code == 200

    def test_list_workflows(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/workflows", headers=auth_headers())
            assert resp.status_code == 200

    def test_get_workflow(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/workflows/nonexistent", headers=auth_headers())
            assert resp.status_code == 404

    def test_list_templates(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/workflows/templates", headers=auth_headers())
            assert resp.status_code == 200

    def test_create_template(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.post("/api/v1/workflows/templates", json={
                "name": "Template",
                "steps": [{"name": "Step1", "action": "agent_task"}],
            }, headers=auth_headers())
            assert resp.status_code == 200


class TestToolAPI:
    def test_list_tools(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/tools", headers=auth_headers())
            assert resp.status_code == 200

    def test_execute_tool(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.post("/api/v1/tools/calculator/execute", json={
                "expression": "2+2",
            }, headers=auth_headers())
            assert resp.status_code == 200


class TestAnalyticsAPI:
    def test_agent_analytics(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/analytics/agents", headers=auth_headers())
            assert resp.status_code == 200

    def test_tool_analytics(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/analytics/tools", headers=auth_headers())
            assert resp.status_code == 200


class TestCollaborationAPI:
    def test_create_collaboration(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.post("/api/v1/collaborations?goal=Test", headers=auth_headers())
            assert resp.status_code == 200

    def test_list_collaborations(self, client):
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.get("/api/v1/collaborations", headers=auth_headers())
            assert resp.status_code == 200
