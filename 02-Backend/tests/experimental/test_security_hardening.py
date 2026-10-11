"""Tests for the security hardening module."""

from __future__ import annotations

import time
import unittest

from app.security_hardening import (
    AuditLog,
    CodeExecutionError,
    JWTError,
    PolicyDecision,
    Principal,
    URLSafetyError,
    _is_private_ip,
    check_admin,
    check_ownership,
    hash_api_key,
    is_admin_role,
    is_safe_redirect,
    jwt_decode,
    jwt_encode,
    principal_from_jwt_claims,
    safe_exec,
    scrub_dict,
    scrub_text,
    validate_url,
    verify_api_key,
)


SECRET = "test-secret-key-for-jwt-signing-do-not-use-in-prod"


class JWTTest(unittest.TestCase):
    def test_roundtrip(self):
        token = jwt_encode({"sub": "u1", "role": "user"}, secret=SECRET, expires_in=60)
        claims = jwt_decode(token, secret=SECRET)
        self.assertEqual(claims["sub"], "u1")
        self.assertEqual(claims["role"], "user")

    def test_expired(self):
        token = jwt_encode({"sub": "u1"}, secret=SECRET, expires_in=-1)
        with self.assertRaises(JWTError):
            jwt_decode(token, secret=SECRET)

    def test_invalid_signature(self):
        token = jwt_encode({"sub": "u1"}, secret=SECRET)
        with self.assertRaises(JWTError):
            jwt_decode(token, secret="wrong-secret")

    def test_malformed(self):
        with self.assertRaises(JWTError):
            jwt_decode("not-a-jwt", secret=SECRET)

    def test_algorithms_restricted(self):
        token = jwt_encode({"sub": "u1"}, secret=SECRET)
        with self.assertRaises(JWTError):
            jwt_decode(token, secret=SECRET, algorithms=["RS256"])


class RoleTest(unittest.TestCase):
    def test_admin_roles(self):
        self.assertTrue(is_admin_role("admin"))
        self.assertTrue(is_admin_role("owner"))
        self.assertTrue(is_admin_role("superadmin"))
        self.assertTrue(is_admin_role("ADMIN"))

    def test_non_admin_roles(self):
        self.assertFalse(is_admin_role("user"))
        self.assertFalse(is_admin_role(""))
        self.assertFalse(is_admin_role("guest"))

    def test_legacy_string_check_bypassed(self):
        """The legacy ':admin' in authorization hack is now safely
        replaced with explicit role checks."""
        self.assertFalse(is_admin_role("notadmin"))
        self.assertFalse(is_admin_role("admin_user"))


class PrincipalTest(unittest.TestCase):
    def test_from_jwt_claims(self):
        claims = {
            "sub": "user-123",
            "email": "u@example.com",
            "app_metadata": {"role": "admin"},
            "workspace_id": "ws-1",
        }
        p = principal_from_jwt_claims(claims)
        self.assertEqual(p.id, "user-123")
        self.assertEqual(p.role, "admin")
        self.assertEqual(p.workspace_id, "ws-1")
        self.assertTrue(p.is_admin())

    def test_role_from_user_metadata_fallback(self):
        claims = {"sub": "u", "user_metadata": {"role": "editor"}}
        p = principal_from_jwt_claims(claims)
        self.assertEqual(p.role, "editor")
        self.assertFalse(p.is_admin())

    def test_default_role(self):
        claims = {"sub": "u"}
        p = principal_from_jwt_claims(claims)
        self.assertEqual(p.role, "user")


class OwnershipTest(unittest.TestCase):
    def test_admin_can_access_anything(self):
        admin = Principal(id="admin-1", email="a@e.com", role="admin")
        self.assertTrue(check_ownership(admin, "anyone"))

    def test_user_owns_resource(self):
        user = Principal(id="u-1", email="u@e.com", role="user")
        self.assertTrue(check_ownership(user, "u-1"))

    def test_user_cannot_access_others(self):
        user = Principal(id="u-1", email="u@e.com", role="user")
        self.assertFalse(check_ownership(user, "u-2"))


class URLSafetyTest(unittest.TestCase):
    def test_blocks_private_ip(self):
        with self.assertRaises(URLSafetyError):
            validate_url("http://127.0.0.1/admin", allow_private=False)

    def test_blocks_private_ip_v6(self):
        with self.assertRaises(URLSafetyError):
            validate_url("http://[::1]/admin", allow_private=False)

    def test_blocks_localhost(self):
        with self.assertRaises(URLSafetyError):
            validate_url("http://localhost/admin", allow_private=False)

    def test_blocks_metadata_service(self):
        with self.assertRaises(URLSafetyError):
            validate_url(
                "http://169.254.169.254/latest/meta-data/",
                allow_private=False,
            )

    def test_blocks_file_scheme(self):
        with self.assertRaises(URLSafetyError):
            validate_url("file:///etc/passwd")

    def test_blocks_javascript_scheme(self):
        with self.assertRaises(URLSafetyError):
            validate_url("javascript:alert(1)")

    def test_allows_https(self):
        url = validate_url("https://example.com/path")
        self.assertEqual(url, "https://example.com/path")

    def test_allow_private_flag(self):
        url = validate_url("http://127.0.0.1", allow_private=True)
        self.assertEqual(url, "http://127.0.0.1")

    def test_redirect_safety(self):
        self.assertTrue(is_safe_redirect("https://a.com", "https://b.com"))
        self.assertTrue(is_safe_redirect("https://a.com", "/local/path"))
        self.assertFalse(is_safe_redirect("https://a.com", "http://localhost"))


class ScrubberTest(unittest.TestCase):
    def test_aws_key_scrubbed(self):
        text = "AKIAABCDEFGHIJKLMNOP"
        scrubbed = scrub_text(text)
        self.assertIn("REDACTED", scrubbed)
        self.assertNotIn("AKIAABCDEF", scrubbed)

    def test_github_token_scrubbed(self):
        text = "token=ghp_abcdefghijklmnopqrstuvwxyz0123456789"
        scrubbed = scrub_text(text)
        self.assertIn("REDACTED", scrubbed)

    def test_jwt_scrubbed(self):
        text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
        scrubbed = scrub_text(text)
        self.assertIn("REDACTED", scrubbed)

    def test_dict_scrub(self):
        data = {
            "aws_key": "AKIAABCDEFGHIJKLMNOP",
            "nested": {"github": "ghp_abcdefghijklmnopqrstuvwxyz0123456789"},
        }
        scrubbed = scrub_dict(data)
        self.assertIn("REDACTED", scrubbed["aws_key"])
        self.assertIn("REDACTED", scrubbed["nested"]["github"])


class APIKeyTest(unittest.TestCase):
    def test_hash_and_verify(self):
        key = "ak_test_1234567890"
        salt = "salt-1"
        h = hash_api_key(key, salt)
        self.assertTrue(verify_api_key(key, h, salt))
        self.assertFalse(verify_api_key("wrong-key", h, salt))
        self.assertFalse(verify_api_key(key, h, "wrong-salt"))


class AuditLogTest(unittest.TestCase):
    def test_record_and_query(self):
        log = AuditLog()
        log.record("u1", "read", "/x", outcome="success")
        log.record("u1", "delete", "/y", outcome="denied")
        events = log.query(actor="u1")
        self.assertEqual(len(events), 2)

    def test_query_by_action(self):
        log = AuditLog()
        log.record("u1", "login", "/auth", outcome="success")
        log.record("u1", "logout", "/auth", outcome="success")
        events = log.query(action="login")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "login")


class SafeExecTest(unittest.TestCase):
    def test_simple_print(self):
        output = safe_exec("print('hello world')")
        self.assertIn("hello world", output)

    def test_blocks_os_import(self):
        with self.assertRaises(CodeExecutionError):
            safe_exec("import os; os.system('echo HACKED')")

    def test_blocks_subprocess(self):
        with self.assertRaises(CodeExecutionError):
            safe_exec("import subprocess; subprocess.run(['echo', 'HACKED'])")

    def test_timeout(self):
        with self.assertRaises(CodeExecutionError):
            safe_exec("while True: pass", timeout_s=1.0)

    def test_truncates_long_output(self):
        output = safe_exec("print('A' * 100)")
        self.assertLessEqual(len(output), 11_000)

    def test_syntax_error_caught(self):
        with self.assertRaises(CodeExecutionError):
            safe_exec("def foo(:\n  pass")

    def test_safe_builtins(self):
        output = safe_exec("print(sum([1, 2, 3, 4]))")
        self.assertIn("10", output)


class PrivateIPTest(unittest.TestCase):
    def test_detects_loopback(self):
        self.assertTrue(_is_private_ip("127.0.0.1"))

    def test_detects_private(self):
        self.assertTrue(_is_private_ip("10.0.0.1"))
        self.assertTrue(_is_private_ip("192.168.1.1"))
        self.assertTrue(_is_private_ip("172.16.0.1"))

    def test_detects_public(self):
        self.assertFalse(_is_private_ip("8.8.8.8"))
        self.assertFalse(_is_private_ip("1.1.1.1"))

    def test_invalid_ip(self):
        self.assertFalse(_is_private_ip("not-an-ip"))


if __name__ == "__main__":
    unittest.main()
