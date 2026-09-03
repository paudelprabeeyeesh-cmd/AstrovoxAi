"""Tests for the IAM, per-request Supabase, and hardened rate limiter."""

from __future__ import annotations

import unittest

from app.iam import (
    get_jwt_algorithms,
    get_jwt_secret,
)
from app.rate_limit_hardened import (
    DEFAULT_LIMITS,
    InProcessLimiter,
    RateLimitConfig,
    SlidingWindowCounter,
)
from app.security_hardening import (
    JWTError,
    Principal,
    is_admin_role,
    jwt_decode,
    jwt_encode,
    principal_from_jwt_claims,
)
from app.supabase_authenticated import (
    SupabaseClient,
    SupabaseTable,
    get_anonymous_supabase,
    get_supabase,
)


SECRET = "test-secret-key-for-iam-tests-do-not-use-in-prod"


class JWTIAMTest(unittest.TestCase):
    def test_admin_principal_from_jwt_claims(self):
        claims = jwt_encode(
            {
                "sub": "u-1",
                "email": "admin@e.com",
                "app_metadata": {"role": "admin"},
            },
            secret=SECRET,
            expires_in=60,
        )
        decoded = jwt_decode(claims, secret=SECRET)
        principal = principal_from_jwt_claims(decoded)
        self.assertEqual(principal.id, "u-1")
        self.assertEqual(principal.role, "admin")
        self.assertTrue(principal.is_admin())

    def test_user_principal_not_admin(self):
        claims = jwt_encode(
            {"sub": "u-1", "role": "user"}, secret=SECRET
        )
        decoded = jwt_decode(claims, secret=SECRET)
        principal = principal_from_jwt_claims(decoded)
        self.assertFalse(principal.is_admin())
        self.assertEqual(principal.role, "user")

    def test_role_fallback_to_user_metadata(self):
        claims = {"sub": "u-1", "user_metadata": {"role": "editor"}}
        principal = principal_from_jwt_claims(claims)
        self.assertEqual(principal.role, "editor")

    def test_legacy_string_check_bypassed(self):
        """The ':admin' in authorization hack is no longer relied upon."""
        self.assertFalse(is_admin_role("notadmin"))
        self.assertFalse(is_admin_role(""))
        self.assertTrue(is_admin_role("admin"))

    def test_principal_from_jwt_preserves_workspace(self):
        claims = {"sub": "u-1", "workspace_id": "ws-42"}
        principal = principal_from_jwt_claims(claims)
        self.assertEqual(principal.workspace_id, "ws-42")


class PerRequestSupabaseTest(unittest.TestCase):
    def setUp(self):
        import os
        os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
        os.environ.setdefault("SUPABASE_ANON_KEY", "fake-anon-key")
        # Reset module-level clients so they pick up the env vars
        import importlib
        import app.supabase_authenticated as mod
        importlib.reload(mod)

    def test_anonymous_client_uses_anon_key(self):
        client = get_anonymous_supabase()
        self.assertIn("apikey", client.headers)
        self.assertNotIn("Authorization", client.headers)

    def test_user_client_no_jwt(self):
        principal = Principal(
            id="u-1",
            email="u@e.com",
            role="user",
            raw_claims={},
        )
        client = get_supabase(principal)
        self.assertIn("apikey", client.headers)

    def test_user_client_with_jwt(self):
        principal = Principal(
            id="u-1",
            email="u@e.com",
            role="user",
            raw_claims={"token": "test-jwt-token"},
        )
        client = get_supabase(principal)
        self.assertEqual(client.headers.get("Authorization"), "Bearer test-jwt-token")

    def test_table_query_builder(self):
        client = SupabaseClient(
            "https://example.supabase.co", "fake-key", jwt="jwt"
        )
        table = client.table("conversations").select("id,title").eq("user_id", "u-1")
        url = table._build_url()
        self.assertIn("select=id%2Ctitle", url)
        self.assertIn("user_id=eq.u-1", url)

    def test_table_in_filter(self):
        client = SupabaseClient("https://x.supabase.co", "k")
        table = client.table("items").select("*").in_("id", [1, 2, 3])
        url = table._build_url()
        self.assertIn("id=in.%281%2C2%2C3%29", url)

    def test_table_order_and_limit(self):
        client = SupabaseClient("https://x.supabase.co", "k")
        table = (
            client.table("items")
            .select("*")
            .order("created_at", desc=True)
            .limit(10)
        )
        url = table._build_url()
        self.assertIn("order=created_at.desc", url)
        self.assertIn("limit=10", url)


class RateLimiterTest(unittest.TestCase):
    def test_default_policies_present(self):
        for key in (
            "auth_login",
            "api_authenticated",
            "code_execution",
        ):
            self.assertIn(key, DEFAULT_LIMITS)

    def test_sliding_window_allows_then_blocks(self):
        counter = SlidingWindowCounter(limit=3, window_seconds=60)
        self.assertEqual(counter.hit(1), (True, 2, 0))
        self.assertEqual(counter.hit(1), (True, 1, 0))
        self.assertEqual(counter.hit(1), (True, 0, 0))
        allowed, remaining, reset = counter.hit(1)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(reset, 0)

    def test_in_process_limiter(self):
        limiter = InProcessLimiter()
        result = limiter.check("auth_login", "user-1")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["limit"], 5)
        self.assertEqual(result["window_seconds"], 60)

    def test_in_process_limiter_blocks_after_limit(self):
        limiter = InProcessLimiter()
        for _ in range(5):
            limiter.check("auth_login", "user-1")
        result = limiter.check("auth_login", "user-1")
        self.assertFalse(result["allowed"])

    def test_in_process_limiter_separates_identities(self):
        limiter = InProcessLimiter()
        for _ in range(5):
            limiter.check("auth_login", "user-1")
        result = limiter.check("auth_login", "user-2")
        self.assertTrue(result["allowed"])

    def test_custom_config(self):
        limiter = InProcessLimiter()
        limiter.configure(
            "my_endpoint",
            RateLimitConfig("my_endpoint", 2, 1),
        )
        self.assertTrue(limiter.check("my_endpoint", "x")["allowed"])
        self.assertTrue(limiter.check("my_endpoint", "x")["allowed"])
        self.assertFalse(limiter.check("my_endpoint", "x")["allowed"])

    def test_reset(self):
        limiter = InProcessLimiter()
        for _ in range(5):
            limiter.check("auth_login", "user-1")
        limiter._buckets["auth_login:user-1"].reset()
        self.assertTrue(limiter.check("auth_login", "user-1")["allowed"])


if __name__ == "__main__":
    unittest.main()
