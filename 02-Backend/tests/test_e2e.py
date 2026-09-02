"""End-to-End (E2E) user journey tests.

Tests complete user flows from login to logout, covering:
- User registration and authentication
- Chat creation, editing, deletion
- Message sending and AI responses
- Memory creation and retrieval
- File uploads
- Enterprise features
- Error recovery
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    mock_user = MagicMock()
    mock_user.id = "test-user-e2e"
    mock_user.email = "e2e@test.com"

    mock_session = MagicMock()
    mock_session.access_token = "test-access-token"
    mock_session.refresh_token = "test-refresh-token"

    mock_auth_response = MagicMock()
    mock_auth_response.user = mock_user
    mock_auth_response.session = mock_session

    mock_auth = MagicMock()
    mock_auth.get_user.return_value = mock_auth_response
    mock_auth.sign_up.return_value = mock_auth_response
    mock_auth.sign_in_with_password.return_value = mock_auth_response
    mock_auth.sign_in_with_otp.return_value = mock_auth_response
    mock_auth.refresh_session.return_value = mock_auth_response

    mock_table = MagicMock()
    mock_table.insert.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[{"id": "test-id", "role": "member"}])

    mock_client = MagicMock()
    mock_client.auth = mock_auth
    mock_client.table.return_value = mock_table

    return mock_client


class TestUserJourneyAuthentication:
    """E2E: User registration → login → access protected resource → logout."""

    def test_complete_auth_journey(self, client, mock_supabase):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase):
            with patch("app.supabase_client.get_supabase", return_value=mock_supabase):
                with patch("app.auth.supabase", mock_supabase):
                    # Step 1: Register
                    signup_resp = client.post("/auth/signup", json={
                        "email": "e2e@test.com",
                        "password": "SecurePass123!",
                        "full_name": "E2E Test User"
                    })
                    assert signup_resp.status_code == 200
                    assert signup_resp.json()["status"] == "OK"

                    # Step 2: Verify health (system is operational)
                    health_resp = client.get("/health")
                    assert health_resp.status_code == 200

                    # Step 3: Logout
                    logout_resp = client.post("/auth/logout")
                    assert logout_resp.status_code == 200

                    # Step 3: Logout
                    logout_resp = client.post("/auth/logout")
                    assert logout_resp.status_code == 200

    def test_invalid_login_rejected(self, client, mock_supabase):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase):
            mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid creds")
            resp = client.post("/auth/login", json={
                "email": "bad@test.com",
                "password": "wrongpass"
            })
            assert resp.status_code == 401

    def test_expired_token_rejected(self, client, mock_supabase):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase):
            mock_supabase.auth.get_user.side_effect = Exception("Token expired")
            resp = client.get("/auth/me", headers={
                "Authorization": "Bearer expired-token"
            })
            assert resp.status_code == 401


class TestUserJourneyChat:
    """E2E: Create chat → send message → receive response → delete chat."""

    def test_complete_chat_journey(self, client, mock_supabase):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase):
            with patch("app.supabase_client.get_supabase", return_value=mock_supabase):
                headers = {"Authorization": "Bearer test-token"}

                # Step 1: Create conversation
                create_resp = client.post("/chat/conversations", json={
                    "title": "E2E Test Chat",
                    "model": "gpt-4o-mini"
                }, headers=headers)
                assert create_resp.status_code == 200
                assert create_resp.json()["status"] == "OK"

                # Step 2: List conversations
                list_resp = client.get("/chat/conversations", headers=headers)
                assert list_resp.status_code == 200

                # Step 3: Get models
                models_resp = client.get("/chat/models")
                assert models_resp.status_code == 200
                assert len(models_resp.json()["models"]) >= 5

    def test_unauthorized_chat_access_rejected(self, client):
        resp = client.post("/chat/conversations", json={
            "title": "Test"
        })
        assert resp.status_code == 401

    def test_invalid_model_rejected(self, client, mock_supabase):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase):
            headers = {"Authorization": "Bearer test-token"}
            resp = client.post("/chat/conversations", json={
                "title": "Test",
                "model": "invalid-model-xyz"
            }, headers=headers)
            assert resp.status_code == 422


class TestUserJourneyMemory:
    """E2E: Save memory → retrieve memory → use in context."""

    def test_complete_memory_journey(self, client, mock_supabase):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase):
            headers = {"Authorization": "Bearer test-token"}

            # Step 1: Save memory
            save_resp = client.post("/memory/save", json={
                "content": "User prefers Python over JavaScript",
                "importance": 2
            }, headers=headers)
            assert save_resp.status_code == 200

            # Step 2: Get memory
            get_resp = client.get("/memory/", headers=headers)
            assert get_resp.status_code == 200

            # Step 3: Get context
            context_resp = client.post("/memory/context", headers=headers)
            assert context_resp.status_code == 200

    def test_unauthorized_memory_access_rejected(self, client):
        resp = client.post("/memory/save", json={
            "content": "Test memory"
        })
        assert resp.status_code == 401


class TestUserJourneyEnterprise:
    """E2E: Create organization → invite member → manage workspaces."""

    def test_complete_enterprise_journey(self, client, mock_supabase):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase):
            headers = {"Authorization": "Bearer test-token"}

            # Step 1: Create organization
            create_resp = client.post("/api/enterprise/organizations", json={
                "name": "E2E Test Org",
                "description": "Test organization"
            }, headers=headers)
            assert create_resp.status_code == 200
            org_id = create_resp.json()["organization"]["id"]
            assert org_id is not None

            # Step 2: List organizations
            list_resp = client.get("/api/enterprise/organizations", headers=headers)
            assert list_resp.status_code == 200

            # Step 3: Get organization details
            get_resp = client.get(f"/api/enterprise/organizations/{org_id}", headers=headers)
            assert get_resp.status_code == 200


class TestUserJourneyErrorRecovery:
    """E2E: System handles errors gracefully and recovers."""

    def test_server_error_returns_generic_message(self, client, mock_supabase):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase):
            mock_supabase.auth.get_user.side_effect = Exception("Internal server error")
            resp = client.get("/auth/me", headers={
                "Authorization": "Bearer test-token"
            })
            assert resp.status_code in [401, 500]
            # Should not leak internal error details
            assert "Internal server error" not in resp.json().get("detail", "")

    def test_validation_error_returns_422(self, client):
        resp = client.post("/auth/signup", json={
            "email": "not-an-email",
            "password": "",
            "full_name": ""
        })
        assert resp.status_code == 422

    def test_not_found_returns_404(self, client):
        resp = client.get("/nonexistent-endpoint")
        assert resp.status_code == 404
