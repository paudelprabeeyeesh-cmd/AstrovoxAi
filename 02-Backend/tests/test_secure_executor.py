"""Tests for the secure code executor."""

from __future__ import annotations

import unittest

from app.secure_executor import (
    ExecutionResult,
    SandboxConfig,
    execute_python,
    execute_user_code,
)
from app.security_hardening import Principal


class AdminPrincipal:
    def __init__(self):
        self.id = "admin-1"
        self.email = "admin@e.com"
        self.role = "admin"
        self.scopes = set()
        self.workspace_id = None
        self.raw_claims = {}
        self.authenticated_via = "jwt"

    def is_admin(self):
        return True

    def has_scope(self, scope):
        return scope in self.scopes

    def to_dict(self):
        return {"id": self.id, "role": self.role}


class UserPrincipal:
    def __init__(self):
        self.role = "user"

    def is_admin(self):
        return False

    def has_scope(self, scope):
        return False


class ExecutePythonTest(unittest.TestCase):
    def test_simple_print(self):
        result = execute_python("print('hello sandbox')", principal=AdminPrincipal())
        self.assertTrue(result.success)
        self.assertIn("hello sandbox", result.output)

    def test_arithmetic(self):
        result = execute_python("print(2 + 3 * 4)", principal=AdminPrincipal())
        self.assertIn("14", result.output)

    def test_rejects_non_admin(self):
        result = execute_python("print('hi')", principal=UserPrincipal())
        self.assertFalse(result.success)
        self.assertIn("admin", result.error)

    def test_allows_admin(self):
        result = execute_python("print('hi')", principal=AdminPrincipal())
        self.assertTrue(result.success)

    def test_blocks_os_import(self):
        result = execute_python(
            "import os; os.system('echo HACKED')",
            principal=AdminPrincipal(),
        )
        self.assertFalse(result.success)

    def test_blocks_subprocess(self):
        result = execute_python(
            "import subprocess; subprocess.run(['echo', 'HACKED'])",
            principal=AdminPrincipal(),
        )
        self.assertFalse(result.success)

    def test_timeout(self):
        config = SandboxConfig(timeout_s=1.0)
        result = execute_python(
            "while True: pass",
            config=config,
            principal=AdminPrincipal(),
        )
        self.assertTrue(result.timed_out)
        self.assertFalse(result.success)

    def test_rejects_non_string(self):
        result = execute_python(12345, principal=AdminPrincipal())
        self.assertFalse(result.success)
        self.assertIn("string", result.error)

    def test_rejects_oversized_code(self):
        big_code = "x = 1\n" * 100_000
        result = execute_python(big_code, principal=AdminPrincipal())
        self.assertFalse(result.success)
        self.assertIn("length", result.error)

    def test_custom_config(self):
        config = SandboxConfig(timeout_s=2.0, max_output_chars=100)
        result = execute_python(
            "print('A' * 50)",
            config=config,
            principal=AdminPrincipal(),
        )
        self.assertTrue(result.success)
        self.assertLessEqual(len(result.output), 200)

    def test_none_principal_works(self):
        """When no principal is given, execution is allowed (for trusted
        internal callers)."""
        result = execute_python("print('internal')")
        self.assertTrue(result.success)

    def test_syntax_error_caught(self):
        result = execute_python("def foo(:\n  pass", principal=AdminPrincipal())
        self.assertFalse(result.success)

    def test_exit_code_propagated(self):
        config = SandboxConfig(allow_imports=True)
        result = execute_python(
            "import sys; sys.exit(7)",
            config=config,
            principal=AdminPrincipal(),
        )
        self.assertEqual(result.exit_code, 7)

    def test_cross_platform_without_resource_module(self):
        """Execution must succeed even when the `resource` module is
        unavailable, as is the case on Windows."""
        import app.secure_executor as se

        original = getattr(se, "resource", None)
        try:
            se.resource = None  # type: ignore[attr-defined]
            result = execute_python(
                "print('no resource module')",
                principal=AdminPrincipal(),
            )
            self.assertTrue(result.success)
            self.assertIn("no resource module", result.output)
        finally:
            se.resource = original
