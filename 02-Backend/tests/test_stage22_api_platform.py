"""Tests for the public API platform (Stage 22 step 3)."""

from __future__ import annotations

import time
import unittest

from app.ecosystem.api_platform import (
    ApiAnalytics,
    ApiErrorCode,
    ApiKeyStore,
    ApiRegistry,
    OAuthServer,
    RateLimitPolicy,
    RateLimiter,
    RateLimitScope,
    TokenBucket,
    api_error,
    sign_payload,
    verify_signature,
)


class RateLimiterTest(unittest.TestCase):
    def test_default_policies(self):
        limiter = RateLimiter()
        result = limiter.check("authenticated", "key1")
        self.assertTrue(result["allowed"])
        self.assertGreaterEqual(result["remaining"], 0)

    def test_burst_window(self):
        policy = RateLimitPolicy("tiny", RateLimitScope.PER_KEY, limit=2, window_seconds=60)
        limiter = RateLimiter([policy])
        self.assertTrue(limiter.check("tiny", "k")["allowed"])
        self.assertTrue(limiter.check("tiny", "k")["allowed"])
        self.assertFalse(limiter.check("tiny", "k")["allowed"])

    def test_token_bucket(self):
        bucket = TokenBucket(limit=3, window=60)
        self.assertTrue(bucket.consume(1)[0])
        self.assertTrue(bucket.consume(1)[0])
        self.assertTrue(bucket.consume(1)[0])
        self.assertFalse(bucket.consume(1)[0])
        self.assertEqual(bucket.remaining(), 0)

    def test_add_policy(self):
        limiter = RateLimiter()
        policy = RateLimitPolicy("custom", RateLimitScope.PER_KEY, 10, 60)
        limiter.add_policy(policy)
        self.assertIn("custom", limiter.policies)


class ApiKeyStoreTest(unittest.TestCase):
    def test_issue_and_verify(self):
        store = ApiKeyStore()
        record, key, secret = store.issue("owner", "lbl", ["read", "write"])
        verified = store.verify(key, secret)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.id, record.id)

    def test_verify_wrong_secret(self):
        store = ApiKeyStore()
        _, key, _ = store.issue("o", "l", ["read"])
        self.assertIsNone(store.verify(key, "wrong"))

    def test_revoke(self):
        store = ApiKeyStore()
        record, key, secret = store.issue("o", "l", ["read"])
        store.revoke(record.id)
        self.assertIsNone(store.verify(key, secret))

    def test_list_by_owner(self):
        store = ApiKeyStore()
        store.issue("owner1", "k1", ["read"])
        store.issue("owner1", "k2", ["read"])
        store.issue("owner2", "k3", ["read"])
        self.assertEqual(len(store.list("owner1")), 2)
        self.assertEqual(len(store.list("owner2")), 1)


class OAuthServerTest(unittest.TestCase):
    def test_full_flow(self):
        server = OAuthServer()
        client, secret = server.register_client("demo", ["https://x"], ["read"])
        code = server.authorization_code(client.id, "user-1", "https://x", "read", state="abc")
        token = server.exchange_code(code, client.id, "https://x")
        self.assertIsNotNone(token)
        self.assertEqual(token.scope, "read")
        introspected = server.introspect(token.access_token)
        self.assertTrue(introspected["active"])

    def test_expired_code(self):
        server = OAuthServer()
        client, _ = server.register_client("demo", ["https://x"], ["read"])
        code = server.authorization_code(client.id, "user", "https://x", "read")
        # Force expiration
        server._codes[code]["expires_at"] = 0
        self.assertIsNone(server.exchange_code(code, client.id, "https://x"))

    def test_client_credentials(self):
        server = OAuthServer()
        client, secret = server.register_client("demo", [])
        token = server.client_credentials(client.id, "read")
        self.assertIsNotNone(token)
        self.assertEqual(token.user_id, None)

    def test_refresh_token(self):
        server = OAuthServer()
        client, _ = server.register_client("demo", [])
        token = server.client_credentials(client.id, "read")
        new_token = server.refresh(token.refresh_token)
        self.assertIsNotNone(new_token)
        self.assertNotEqual(new_token.access_token, token.access_token)

    def test_introspect_invalid(self):
        server = OAuthServer()
        self.assertIsNone(server.introspect("invalid"))


class SignatureTest(unittest.TestCase):
    def test_roundtrip(self):
        payload = b"hello"
        secret = "topsecret"
        signature = sign_payload(payload, secret)
        self.assertTrue(verify_signature(payload, signature, secret))

    def test_replay_protection(self):
        payload = b"hello"
        secret = "topsecret"
        signature = sign_payload(payload, secret, timestamp=1)
        self.assertFalse(verify_signature(payload, signature, secret))

    def test_invalid_signature(self):
        self.assertFalse(verify_signature(b"hello", "garbage", "secret"))

    def test_missing_signature(self):
        self.assertFalse(verify_signature(b"hello", "", "secret"))


class AnalyticsTest(unittest.TestCase):
    def test_record_and_summary(self):
        analytics = ApiAnalytics()
        for i in range(5):
            analytics.record(
                ApiCall(
                    timestamp=time.time(),
                    endpoint="/v1/chat/completions",
                    method="POST",
                    status=200 if i % 2 else 500,
                    latency_ms=10 + i,
                    key_id="k",
                )
            )
        summary = analytics.summary()
        self.assertEqual(summary["total_calls"], 5)
        self.assertGreater(summary["error_rate"], 0)

    def test_endpoint_perf(self):
        analytics = ApiAnalytics()
        for i in range(10):
            analytics.record(
                ApiCall(
                    timestamp=time.time(),
                    endpoint="/v1/chat",
                    method="POST",
                    status=200,
                    latency_ms=10 + i,
                )
            )
        perf = analytics.endpoint_perf("POST /v1/chat")
        self.assertEqual(perf["count"], 10)


class ErrorEnvelopeTest(unittest.TestCase):
    def test_envelope(self):
        env = api_error(ApiErrorCode.FORBIDDEN, "denied", 403, scope="admin")
        self.assertEqual(env["error"]["code"], "forbidden")
        self.assertEqual(env["error"]["status"], 403)
        self.assertEqual(env["error"]["details"]["scope"], "admin")


class ApiRegistryTest(unittest.TestCase):
    def test_register_and_list(self):
        registry = ApiRegistry()
        ep = ApiEndpoint(
            name="chat",
            method="POST",
            path="/v1/chat/completions",
            handler=lambda: None,
            description="chat",
        )
        registry.register(ep)
        items = registry.list("v1")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "chat")


if __name__ == "__main__":
    unittest.main()