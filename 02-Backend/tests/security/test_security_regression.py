"""Security regression tests for AstrovoxAI backend."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth.auth import (
    MAX_FAILED_ATTEMPTS,
    LOCKOUT_MINUTES,
    _check_brute_force,
    _record_login_attempt,
)
from app.middleware.csrf import CSRFMiddleware
from app.middleware.request_limits import (
    RequestTimeoutMiddleware,
    PayloadSizeLimitMiddleware,
)
from app.middleware.security.security_headers import SecurityHeadersMiddleware
from app.utils.auth.auth_utils import get_current_user
from app.iam import get_jwt_secret


class TestAnonymousAuthRemoved(unittest.TestCase):
    """Ensure auth_utils no longer returns anonymous identity on invalid tokens."""

    def test_no_anonymous_fallback_on_invalid_token(self):
        with patch("app.utils.auth.auth_utils.get_supabase") as mock_sb:
            mock_client = MagicMock()
            mock_client.auth.get_user.return_value = MagicMock(user=None)
            mock_sb.return_value = mock_client

            from fastapi.security import HTTPAuthorizationCredentials
            from app.utils.auth.auth_utils import security_scheme

            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="invalid-token"
            )
            with self.assertRaises(Exception) as ctx:
                import asyncio
                asyncio.run(get_current_user(credentials))
            self.assertIn("401", str(ctx.exception) or str(type(ctx.exception)))


class TestJWTSecretFallbackRemoved(unittest.TestCase):
    """Ensure JWT_SECRET fallback is removed."""

    def test_missing_jwt_secret_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            if "JWT_SECRET" in os.environ:
                del os.environ["JWT_SECRET"]
            with self.assertRaises(RuntimeError):
                get_jwt_secret()


class TestCSRFMiddleware(unittest.TestCase):
    """Ensure CSRF middleware blocks unsafe requests without token."""

    def test_post_without_csrf_rejected(self):
        app_with_csrf = app
        app_with_csrf.add_middleware(CSRFMiddleware)
        client = TestClient(app_with_csrf)

        response = client.post("/auth/login", json={"email": "a@b.com", "password": "x"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", response.json()["detail"])


class TestBruteForceLockout(unittest.TestCase):
    """Ensure login brute-force lockout works."""

    def test_lockout_after_max_failures(self):
        ip = "10.0.0.1"
        email = "test@example.com"
        for _ in range(MAX_FAILED_ATTEMPTS):
            _record_login_attempt(ip, email, False)
        with self.assertRaises(Exception) as ctx:
            _check_brute_force(ip, email)
        self.assertIn("429", str(ctx.exception) or str(type(ctx.exception)))


class TestStripeWebhookCustomerMapping(unittest.TestCase):
    """Ensure Stripe webhook verifies customer mapping."""

    def test_checkout_session_verifies_customer_mapping(self):
        from app.billing import handle_stripe_webhook

        payload = b'{"type": "checkout.session.completed", "data": {"object": {"customer": "cus_123", "metadata": {"user_id": "user-1"}}}}'
        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_test"}):
            with patch("app.billing.get_db") as mock_get_db:
                mock_conn = MagicMock()
                mock_conn.execute.return_value.fetchone.return_value = None
                mock_get_db.return_value.__enter__.return_value = mock_conn

                with self.assertRaises(ValueError) as ctx:
                    handle_stripe_webhook(payload, "sig")
                self.assertIn("Customer mapping verification failed", str(ctx.exception))


class TestRequestTimeout(unittest.TestCase):
    """Ensure request timeout middleware is present."""

    def test_timeout_middleware_registered(self):
        middleware_classes = [m.cls for m in app.user_middleware]
        self.assertIn(RequestTimeoutMiddleware, middleware_classes)


class TestPayloadSizeLimit(unittest.TestCase):
    """Ensure payload size limit middleware is present."""

    def test_payload_middleware_registered(self):
        middleware_classes = [m.cls for m in app.user_middleware]
        self.assertIn(PayloadSizeLimitMiddleware, middleware_classes)


class TestSecurityHeaders(unittest.TestCase):
    """Ensure security headers are present on responses."""

    def test_security_headers_present(self):
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("x-frame-options", response.headers)
        self.assertIn("x-content-type-options", response.headers)
        self.assertIn("strict-transport-security", response.headers)
        self.assertIn("permissions-policy", response.headers)
        self.assertIn("referrer-policy", response.headers)


class TestRateLimitHeaders(unittest.TestCase):
    """Ensure rate limit headers are present."""

    def test_rate_limit_headers_present(self):
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("x-ratelimit-limit", response.headers)
        self.assertIn("x-ratelimit-remaining", response.headers)


if __name__ == "__main__":
    unittest.main()
