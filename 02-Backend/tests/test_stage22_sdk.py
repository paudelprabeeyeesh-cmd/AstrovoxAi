"""Tests for the official Python SDK (Stage 22 step 8)."""

from __future__ import annotations

import io
import json
import unittest
import urllib.error

from app.ecosystem.sdk import AstrovoxClient, AstrovoxError


class _StubResponse:
    def __init__(self, body, status=200):
        self._body = body
        self.status = status

    def read(self):
        return self._body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class SdkTest(unittest.TestCase):
    def test_sign_and_verify(self):
        secret = "shhh"
        payload = b'{"event":"chat.completed"}'
        signature = AstrovoxClient.sign_payload(payload, secret, timestamp=1_700_000_000)
        import time
        original = time.time
        time.time = lambda: 1_700_000_005
        try:
            self.assertTrue(AstrovoxClient.verify_payload(payload, signature, secret))
        finally:
            time.time = original

    def test_verify_rejects_old(self):
        secret = "shhh"
        payload = b"{}"
        signature = AstrovoxClient.sign_payload(payload, secret, timestamp=1)
        self.assertFalse(AstrovoxClient.verify_payload(payload, signature, secret))

    def test_request_serializes_body(self):
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["headers"] = dict(request.headers)
            captured["body"] = (request.data or b"").decode("utf-8")
            return _StubResponse(json.dumps({"ok": True}))

        client = AstrovoxClient(
            base_url="https://api.astrovox.ai",
            api_key="ak_x",
            api_secret="sk_x",
        )
        import unittest.mock
        with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.list_plugins()
        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["headers"]["X-api-key"], "ak_x")
        self.assertEqual(captured["headers"]["X-api-secret"], "sk_x")

    def test_request_handles_get_no_body(self):
        def fake_urlopen(request, timeout=30):
            return _StubResponse(json.dumps({"ok": True}))

        client = AstrovoxClient(
            base_url="https://api.astrovox.ai", api_key="x", api_secret="y"
        )
        import unittest.mock
        with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.list_plugins()
        self.assertEqual(result, {"ok": True})

    def test_request_raises_on_error(self):
        err = urllib.error.HTTPError(
            url="https://api.astrovox.ai/ecosystem/plugins",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=io.BytesIO(b'{"error":{"message":"boom"}}'),
        )

        def fake_urlopen(request, timeout=30):
            raise err

        client = AstrovoxClient(
            base_url="https://api.astrovox.ai", api_key="x", api_secret="y"
        )
        import unittest.mock
        with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            try:
                client.list_plugins()
            except AstrovoxError as exc:
                self.assertEqual(exc.status, 400)
                self.assertIn("boom", str(exc))
            else:
                self.fail("AstrovoxError not raised")

    def test_request_with_bearer_token(self):
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured["headers"] = dict(request.headers)
            return _StubResponse(json.dumps({"ok": True}))

        client = AstrovoxClient(
            base_url="https://api.astrovox.ai", access_token="token-123"
        )
        import unittest.mock
        with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.list_plugins()
        self.assertEqual(captured["headers"]["Authorization"], "Bearer token-123")

    def test_query_params(self):
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured["url"] = request.full_url
            return _StubResponse(json.dumps({"ok": True}))

        client = AstrovoxClient(base_url="https://api.astrovox.ai", api_key="x", api_secret="y")
        import unittest.mock
        with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.marketplace_search(q="github", category="dev")
        self.assertIn("q=github", captured["url"])
        self.assertIn("category=dev", captured["url"])

    def test_transport_override(self):
        def transport(request):
            return {"ok": True, "via": "transport"}

        client = AstrovoxClient(
            base_url="https://api.astrovox.ai", api_key="x", api_secret="y", transport=transport
        )
        result = client.list_plugins()
        self.assertEqual(result["via"], "transport")


if __name__ == "__main__":
    unittest.main()