import pytest
from sandboxing.permission_checker import PermissionChecker, PermissionProfile
from sandboxing.resource_limiter import ResourceLimiter
from sandboxing.sandbox import Sandbox, SandboxResult


@pytest.fixture
def profile():
    return PermissionProfile(
        allowed_imports={"math"},
        allowed_builtins=PermissionChecker.DEFAULT_ALLOWED_BUILTINS,
        max_execution_time=1.0,
        max_memory_mb=128,
    )


@pytest.fixture
def limiter():
    return ResourceLimiter(max_memory_mb=128, max_execution_time=1.0)


@pytest.fixture
def sandbox(profile, limiter):
    return Sandbox(profile=profile, limiter=limiter)


def test_execute_success(sandbox):
    result = sandbox.execute("1 + 1")
    assert isinstance(result, SandboxResult)
    assert result.success is True
    assert result.permission_denied is False


def test_execute_syntax_error(sandbox):
    result = sandbox.execute("1 +")
    assert result.success is False
    assert "SyntaxError" in result.error


def test_execute_blocked_import(sandbox):
    result = sandbox.execute("import os")
    assert result.success is False
    assert result.permission_denied is True
    assert "blocked imports" in result.error


def test_execute_allowed_import(sandbox):
    result = sandbox.execute("import math\nmath.sqrt(4)")
    assert result.success is True


def test_execute_print_output(sandbox):
    result = sandbox.execute("print('sandboxed')")
    assert result.success is True
    assert "sandboxed" in result.output


def test_sandbox_result_fields(sandbox):
    result = sandbox.execute("1 + 1")
    assert hasattr(result, "success")
    assert hasattr(result, "output")
    assert hasattr(result, "error")
    assert hasattr(result, "permission_denied")


def test_execute_permission_denied_false_on_success(sandbox):
    result = sandbox.execute("math.sqrt(9)")
    assert result.permission_denied is False


def test_execute_empty_string(sandbox):
    result = sandbox.execute("")
    assert result.success is True


def test_execute_multiline_code(sandbox):
    result = sandbox.execute("x = 1\nx += 1\nprint(x)")
    assert result.success is True
    assert "2" in result.output
