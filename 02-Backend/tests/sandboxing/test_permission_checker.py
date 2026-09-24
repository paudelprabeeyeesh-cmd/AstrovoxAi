import pytest
from sandboxing.permission_checker import PermissionChecker, PermissionProfile


@pytest.fixture
def profile():
    return PermissionProfile(
        allowed_imports={"math", "json"},
        allowed_builtins=PermissionChecker.DEFAULT_ALLOWED_BUILTINS,
        max_execution_time=1.0,
        max_memory_mb=128,
    )


def test_check_imports_allowed(profile):
    checker = PermissionChecker(profile)
    blocked = checker.check_imports("import math")
    assert blocked == []


def test_check_imports_blocked(profile):
    checker = PermissionChecker(profile)
    blocked = checker.check_imports("import os")
    assert "os" in blocked


def test_check_imports_from_allowed(profile):
    checker = PermissionChecker(profile)
    blocked = checker.check_imports("from json import loads")
    assert blocked == []


def test_check_imports_from_blocked(profile):
    checker = PermissionChecker(profile)
    blocked = checker.check_imports("from os import path")
    assert "os" in blocked


def test_check_imports_nested_module(profile):
    checker = PermissionChecker(profile)
    blocked = checker.check_imports("import os.path")
    assert "os" in blocked


def test_check_operation_allowed(profile):
    checker = PermissionChecker(profile)
    assert checker.check_operation("calculate_sum") is True


def test_check_operation_disallowed(profile):
    checker = PermissionChecker(profile)
    assert checker.check_operation("os.system") is False


def test_apply_allows_safe_code(profile):
    checker = PermissionChecker(profile)
    assert checker.apply("import math\nmath.sqrt(4)") is True


def test_apply_blocks_unsafe_code(profile):
    checker = PermissionChecker(profile)
    assert checker.apply("import os\nos.system('ls')") is False


def test_build_safe_globals(profile):
    checker = PermissionChecker(profile)
    safe_globals = checker.build_safe_globals()
    assert "__name__" in safe_globals
    assert "__builtins__" in safe_globals
    assert "print" in safe_globals["__builtins__"]
    assert "open" not in safe_globals["__builtins__"]
