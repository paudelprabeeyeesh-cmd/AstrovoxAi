"""Security regression tests.

Tests that previously discovered vulnerabilities remain fixed.
Run these tests to ensure security patches are not reverted.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_supabase_admin():
    """Mock Supabase with admin user."""
    mock_user = MagicMock()
    mock_user.id = "admin-user-id"
    mock_user.email = "admin@test.com"

    mock_response = MagicMock()
    mock_response.user = mock_user

    mock_auth = MagicMock()
    mock_auth.get_user.return_value = mock_response

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[{"role": "admin"}])

    mock_client = MagicMock()
    mock_client.auth = mock_auth
    mock_client.table.return_value = mock_table

    return mock_client


@pytest.fixture
def mock_supabase_regular():
    """Mock Supabase with regular user."""
    mock_user = MagicMock()
    mock_user.id = "regular-user-id"
    mock_user.email = "user@test.com"

    mock_response = MagicMock()
    mock_response.user = mock_user

    mock_auth = MagicMock()
    mock_auth.get_user.return_value = mock_response

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[{"role": "member"}])

    mock_client = MagicMock()
    mock_client.auth = mock_auth
    mock_client.table.return_value = mock_table

    return mock_client


class TestSecurityErrorDetailLeaking:
    """Verify error messages don't leak internal details."""

    def test_storage_error_no_internal_details(self, client, mock_supabase_admin):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase_admin):
            headers = {"Authorization": "Bearer test-token"}
            resp = client.post(
                "/storage/invalid_bucket/upload",
                files={"file": ("test.txt", b"content", "text/plain")},
                headers=headers,
            )
            # Should not leak internal error details
            assert resp.status_code in [400, 403, 500]
            detail = resp.json().get("detail", "")
            assert "traceback" not in detail.lower()
            assert "exception" not in detail.lower()
            assert "sql" not in detail.lower()

    def test_auth_error_no_internal_details(self, client, mock_supabase_admin):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase_admin):
            mock_supabase_admin.auth.get_user.side_effect = Exception("Internal DB error")
            resp = client.get("/auth/me", headers={
                "Authorization": "Bearer bad-token"
            })
            assert resp.status_code == 401
            detail = resp.json().get("detail", "")
            assert "Internal DB error" not in detail

    def test_chat_error_no_internal_details(self, client, mock_supabase_admin):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase_admin):
            headers = {"Authorization": "Bearer test-token"}
            mock_supabase_admin.auth.get_user.side_effect = Exception("DB connection failed")
            resp = client.get("/chat/conversations", headers=headers)
            assert resp.status_code in [401, 500]
            detail = resp.json().get("detail", "")
            assert "DB connection failed" not in detail


class TestSecurityMassAssignment:
    """Verify mass assignment vulnerabilities are fixed."""

    def test_profile_update_rejects_disallowed_fields(self, client, mock_supabase_admin):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase_admin):
            with patch("app.database.update_user_profile") as mock_update:
                mock_update.return_value = None  # Should reject disallowed fields
                # This test verifies that the update_user_profile function
                # has a whitelist of allowed fields
                from app.database import ALLOWED_PROFILE_FIELDS
                assert "role" not in ALLOWED_PROFILE_FIELDS
                assert "is_admin" not in ALLOWED_PROFILE_FIELDS
                assert "id" not in ALLOWED_PROFILE_FIELDS

    def test_conversation_update_rejects_disallowed_fields(self):
        from app.database import ALLOWED_CONVERSATION_FIELDS
        assert "user_id" not in ALLOWED_CONVERSATION_FIELDS
        assert "is_deleted" not in ALLOWED_CONVERSATION_FIELDS

    def test_settings_update_rejects_disallowed_fields(self):
        from app.database import ALLOWED_SETTINGS_FIELDS
        assert "user_id" not in ALLOWED_SETTINGS_FIELDS
        assert "role" not in ALLOWED_SETTINGS_FIELDS


class TestSecurityAuthenticationBypass:
    """Verify authentication cannot be bypassed."""

    def test_missing_auth_header_rejected(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_malformed_auth_header_rejected(self, client, mock_supabase_admin):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase_admin):
            mock_supabase_admin.auth.get_user.side_effect = Exception("Invalid token")
            resp = client.get("/auth/me", headers={
                "Authorization": "NotBearer token"
            })
            assert resp.status_code == 401

    def test_empty_token_rejected(self, client, mock_supabase_admin):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase_admin):
            mock_supabase_admin.auth.get_user.side_effect = Exception("Empty token")
            resp = client.get("/auth/me", headers={
                "Authorization": "Bearer "
            })
            assert resp.status_code == 401


class TestSecurityIDOR:
    """Verify IDOR (Insecure Direct Object Reference) is prevented."""

    def test_chat_messages_require_ownership(self, client, mock_supabase_admin):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase_admin):
            headers = {"Authorization": "Bearer test-token"}
            # The endpoint should verify the user owns the conversation
            resp = client.get("/chat/conversations/99999/messages", headers=headers)
            # Should return 404 (not found) rather than data
            assert resp.status_code in [401, 404]


class TestSecurityInputValidation:
    """Verify input validation is enforced."""

    def test_signup_email_validation(self, client):
        resp = client.post("/auth/signup", json={
            "email": "not-an-email",
            "password": "pass",
            "full_name": "Test"
        })
        assert resp.status_code == 422

    def test_signup_password_required(self, client):
        resp = client.post("/auth/signup", json={
            "email": "test@test.com",
            "password": "",
            "full_name": "Test"
        })
        assert resp.status_code == 422

    def test_message_length_validation(self, client, mock_supabase_admin):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase_admin):
            headers = {"Authorization": "Bearer test-token"}
            resp = client.post("/chat/message", json={
                "conversation_id": 1,
                "message": "",  # Empty message
                "model": "gpt-4"
            }, headers=headers)
            assert resp.status_code == 422

    def test_invalid_model_rejected(self, client, mock_supabase_admin):
        with patch("app.auth_utils.get_supabase", return_value=mock_supabase_admin):
            headers = {"Authorization": "Bearer test-token"}
            resp = client.post("/chat/message", json={
                "conversation_id": 1,
                "message": "Hello",
                "model": "invalid-model-xyz"
            }, headers=headers)
            assert resp.status_code == 422


class TestSecurityRateLimitHeaders:
    """Verify rate limiting headers are present."""

    def test_rate_limit_headers_present(self, client):
        resp = client.get("/health")
        assert "x-ratelimit-limit" in resp.headers
        assert "x-ratelimit-remaining" in resp.headers


class TestSecurityResponseHeaders:
    """Verify security headers are present."""

    def test_security_headers_on_all_endpoints(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "Content-Security-Policy" in resp.headers
        assert "Strict-Transport-Security" in resp.headers
