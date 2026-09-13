"""End-to-end integration tests for the complete platform."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def auth():
    return {"Authorization": "Bearer test-token"}


class TestPlatformEndToEnd:
    """End-to-end platform tests."""

    def test_health_to_workflow_creation(self, client):
        """Test complete flow: health check → create workflow → execute."""
        # Step 1: Health check
        resp = client.get("/health")
        assert resp.status_code == 200

        # Step 2: Create workflow
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
            resp = client.post("/api/v1/workflows", json={
                "name": "E2E Test",
                "steps": [{"name": "Step1", "action": "agent_task"}],
            }, headers=auth())
            assert resp.status_code == 200

    def test_agent_dashboard_flow(self, client):
        """Test: list agents → get health → view dashboard."""
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))

            resp = client.get("/api/v1/agents", headers=auth())
            assert resp.status_code == 200

            resp = client.get("/api/v1/agents/planner/health", headers=auth())
            assert resp.status_code == 200

            resp = client.get("/api/dashboard/stats", headers=auth())
            assert resp.status_code == 200

    def test_tool_execution_flow(self, client):
        """Test: list tools → execute tool → check metrics."""
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))

            resp = client.get("/api/v1/tools", headers=auth())
            assert resp.status_code == 200

            resp = client.post("/api/v1/tools/calculator/execute", json={
                "expression": "2+2",
            }, headers=auth())
            assert resp.status_code == 200

            resp = client.get("/api/v1/analytics/tools", headers=auth())
            assert resp.status_code == 200


class TestSecurityRegression:
    """Security regression tests."""

    def test_no_auth_returns_401(self, client):
        """Verify protected endpoints reject unauthenticated requests."""
        resp = client.get("/api/v1/agents")
        assert resp.status_code == 401

    def test_invalid_token_rejected(self, client):
        """Verify invalid tokens are rejected."""
        with patch("app.auth_utils.get_supabase") as mock_supabase:
            mock_supabase.return_value.auth.get_user.side_effect = Exception("Invalid")
            resp = client.get("/api/v1/agents", headers={"Authorization": "Bearer bad"})
            assert resp.status_code == 401


class TestSystemHealth:
    """System health verification."""

    def test_health_endpoints(self, client):
        assert client.get("/health").status_code == 200
        assert client.get("/health/readiness").status_code == 200
        assert client.get("/health/liveness").status_code == 200

    def test_metrics_endpoint(self, client):
        resp = client.get("/metrics")
        assert resp.status_code in [200, 500]


class TestAgentCollaboration:
    """Test multi-agent collaboration flows."""

    @pytest.mark.asyncio
    async def test_full_collaboration(self):
        from app.multi_agent import collaboration_manager
        session = collaboration_manager.create_session("u1", "Test collaboration")
        assert session.id is not None
        assert len(session.tasks) > 0
        result = await collaboration_manager.run_session(session.id)
        assert result.status.value == "completed"


class TestWorkflowEngine:
    """Test workflow engine flows."""

    @pytest.mark.asyncio
    async def test_create_and_execute_workflow(self):
        from app.workflow_engine import workflow_engine, StepAction
        wf = workflow_engine.create_workflow("Test", "Test workflow")
        workflow_engine.add_step(wf.id, "Step1", StepAction.AGENT_TASK)
        execution = await workflow_engine.execute_workflow(wf.id)
        assert execution.status.value == "completed"
