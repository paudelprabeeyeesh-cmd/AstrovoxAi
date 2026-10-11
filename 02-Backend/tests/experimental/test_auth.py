"""Comprehensive authentication tests."""

import time
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app import auth
from app.main import app
from app.security_hardening import JWTError, jwt_decode, jwt_encode, Principal, AuditLogger

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_supabase_auth():
    mock_response = MagicMock()
    mock_response.user = MagicMock()
    mock_response.user.id = f"user-{uuid.uuid4().hex[:8]}"
    mock_response.user.email = "test@example.com"
    mock_response.session = MagicMock()
    mock_response.session.access_token = "mock-access-token"

    with patch.object(auth, "supabase") as mock_sb:
        mock_sb.auth.sign_up.return_value = mock_response
        mock_sb.auth.sign_in_with_password.return_value = mock_response
        mock_sb.auth.get_user.return_value = mock_response
        mock_sb.auth.reset_password_email.return_value = None
        mock_sb.auth.update_user.return_value = mock_response
        yield mock_sb


@pytest.fixture(autouse=True)
def mock_audit():
    with patch.object(auth, "_audit") as mock_audit_log:
        mock_audit_log.record = MagicMock()
        yield mock_audit_log


class TestAuthEndpoints:
    def test_signup_creates_user(self):
        response = client.post(
            "/auth/signup",
            json={
                "email": f"signup-{int(time.time())}@test.com",
                "password": "SecurePass123!",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "user" in data

    def test_signup_weak_password(self):
        response = client.post(
            "/auth/signup",
            json={
                "email": "weak@test.com",
                "password": "123",
                "full_name": "Test",
            },
        )
        assert response.status_code in (400, 422)

    def test_login_returns_token(self):
        response = client.post(
            "/auth/login",
            json={"email": "login@test.com", "password": "SecurePass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data or "session" in data

    def test_login_invalid_credentials(self):
        response = client.post(
            "/auth/login",
            json={"email": "bad@test.com", "password": "wrongpass"},
        )
        assert response.status_code in (401, 400)

    def test_reset_password(self):
        response = client.post(
            "/auth/reset-password",
            json={"email": "reset@test.com"},
        )
        assert response.status_code in (200, 204)

    def test_oauth_google(self):
        response = client.post(
            "/auth/oauth",
            json={"provider": "google", "access_token": "mock-token"},
        )
        assert response.status_code in (200, 400, 422)


class TestRateLimiting:
    def test_signup_rate_limited(self):
        for _ in range(10):
            client.post(
                "/auth/signup",
                json={"email": "ratelimit@test.com", "password": "SecurePass123!", "full_name": "Test"},
            )
        response = client.post(
            "/auth/signup",
            json={"email": "ratelimit2@test.com", "password": "SecurePass123!", "full_name": "Test"},
        )
        assert response.status_code == 429


class TestAuthSecurity:
    def test_missing_authorization_header(self):
        response = client.get("/api/me")
        assert response.status_code == 401

    def test_malformed_bearer_token(self):
        response = client.get("/api/me", headers={"Authorization": "NotBearer token"})
        assert response.status_code == 401

    def test_expired_token_rejected(self):
        with patch("app.auth_utils.get_supabase") as mock_get_sb:
            mock_sb = MagicMock()
            mock_get_sb.return_value = mock_sb
            mock_sb.auth.get_user.side_effect = Exception("token_expired")
            response = client.get("/api/me", headers={"Authorization": "Bearer expired"})
            assert response.status_code == 401


class TestJWTModule:
    def test_encode_decode_roundtrip(self):
        secret = "test-secret-key"
        payload = {"sub": "user-1", "email": "test@test.com", "role": "user"}
        token = jwt_encode(payload, secret=secret, expires_in=3600)
        decoded = jwt_decode(token, secret=secret)
        assert decoded["sub"] == "user-1"
        assert decoded["email"] == "test@test.com"

    def test_decode_invalid_signature(self):
        token = jwt_encode({"sub": "1"}, secret="correct")
        with pytest.raises(JWTError):
            jwt_decode(token, secret="wrong")

    def test_decode_expired(self):
        secret = "test-secret"
        payload = {"sub": "1", "exp": int(time.time()) - 100}
        token = jwt_encode(payload, secret=secret, expires_in=-100)
        with pytest.raises(JWTError):
            jwt_decode(token, secret=secret)

    def test_decode_malformed(self):
        with pytest.raises(JWTError):
            jwt_decode("not.a.token", secret="secret")

    def test_decode_unsupported_algorithm(self):
        import base64
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(b'{"sub":"1"}').rstrip(b"=").decode()
        token = f"{header}.{payload}.sig"
        with pytest.raises(JWTError):
            jwt_decode(token, secret="secret", algorithms=["RS256"])


class TestPrincipal:
    def test_admin_role(self):
        p = Principal(id="1", email="admin@test.com", role="admin")
        assert p.is_admin()

    def test_user_role_not_admin(self):
        p = Principal(id="1", email="user@test.com", role="user")
        assert not p.is_admin()

    def test_scope_check(self):
        p = Principal(id="1", email="user@test.com", role="user", scopes={"read", "write"})
        assert p.has_scope("read")
        assert not p.has_scope("admin")

    def test_to_dict(self):
        p = Principal(id="1", email="a@b.com", role="superadmin")
        d = p.to_dict()
        assert d["role"] == "superadmin"
        assert d["id"] == "1"


class TestAuditLogger:
    def test_log_authentication_success(self):
        logger = AuditLogger()
        logger.log_authentication("user-1", "10.0.0.1", True, "password")
        events = logger.get_events(user_id="user-1")
        assert len(events) == 1
        assert events[0].event_type == "authentication"
        assert events[0].severity == "info"

    def test_log_authentication_failure(self):
        logger = AuditLogger()
        logger.log_authentication("user-1", "10.0.0.1", False, "password")
        events = logger.get_events()
        assert events[0].severity == "warning"

    def test_log_authorization(self):
        logger = AuditLogger()
        logger.log_authorization("user-1", "10.0.0.1", "/admin", True)
        events = logger.get_events(event_type="authorization")
        assert len(events) == 1
        assert events[0].details["granted"] is True

    def test_log_data_access(self):
        logger = AuditLogger()
        logger.log_data_access("user-1", "10.0.0.1", "documents", "read")
        events = logger.get_events()
        assert events[0].event_type == "data_access"

    def test_get_events_filter_by_user(self):
        logger = AuditLogger()
        logger.log_authentication("user-1", "10.0.0.1", True)
        logger.log_authentication("user-2", "10.0.0.2", False)
        events = logger.get_events(user_id="user-1")
        assert len(events) == 1
        assert events[0].user_id == "user-1"

    def test_get_events_since_timestamp(self):
        logger = AuditLogger()
        past = time.time() - 10
        logger.log_authentication("user-1", "10.0.0.1", True)
        events = logger.get_events(since=past + 5)
        assert len(events) == 1

    def test_get_events_limit(self):
        logger = AuditLogger()
        for _ in range(10):
            logger.log_authentication("user-1", "10.0.0.1", True)
        events = logger.get_events(limit=3)
        assert len(events) == 3
