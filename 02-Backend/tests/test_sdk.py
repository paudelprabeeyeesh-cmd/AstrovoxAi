"""SDK tests for the AstrovoxAI Python SDK."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from app.ecosystem.sdk import AstrovoxClient, AstrovoxError
from app.ecosystem.api_platform import sign_payload, verify_signature as verify_payload


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


class AstrovoxSdkTest(unittest.TestCase):
    def test_sign_and_verify(self):
        secret = "shhh"
        payload = b'{"event":"chat.completed"}'
        signature = sign_payload(payload, secret, timestamp=1_700_000_000)
        with patch("time.time", return_value=1_700_000_005):
            self.assertTrue(verify_payload(payload, signature, secret))

    def test_verify_rejects_old(self):
        secret = "shhh"
        payload = b"{}"
        signature = sign_payload(payload, secret, timestamp=1)
        self.assertFalse(verify_payload(payload, signature, secret))

    def test_request_serializes_body(self):
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["headers"] = dict(request.headers)
            captured["body"] = request.data.decode("utf-8")
            return _StubResponse(json.dumps({"ok": True}))

        client = AstrovoxClient(base_url="https://api.astrovox.ai", api_key="ak_x", api_secret="sk_x")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.list_plugins()
        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["headers"]["X-api-key"], "ak_x")
        self.assertEqual(captured["headers"]["X-api-secret"], "sk_x")

    def test_request_raises_on_error(self):
        def fake_urlopen(request, timeout=30):
            return _StubResponse(json.dumps({"error": {"message": "boom"}}), status=400)

        client = AstrovoxClient(base_url="https://api.astrovox.ai", api_key="x", api_secret="y")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            try:
                client.list_plugins()
            except AstrovoxError as exc:
                self.assertEqual(exc.status, 400)
                self.assertIn("boom", str(exc))
            else:
                self.fail("AstrovoxError not raised")


if __name__ == "__main__":
    unittest.main()