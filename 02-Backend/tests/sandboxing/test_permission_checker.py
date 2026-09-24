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


def test_build_safe_globals_excludes_os(profile):
    checker = PermissionChecker(profile)
    safe_globals = checker.build_safe_globals()
    builtins = safe_globals["__builtins__"]
    assert "os" not in builtins
    assert "system" not in builtins


def test_check_imports_no_imports(profile):
    checker = PermissionChecker(profile)
    assert checker.check_imports("x = 1") == []


def test_check_imports_syntax_error(profile):
    checker = PermissionChecker(profile)
    assert checker.check_imports("1 +") == []


def test_check_imports_multiple_mixed(profile):
    checker = PermissionChecker(profile)
    blocked = checker.check_imports("import math\nimport os")
    assert "os" in blocked
    assert "math" not in blocked


def test_check_imports_as_alias(profile):
    checker = PermissionChecker(profile)
    blocked = checker.check_imports("import os as operating_system")
    assert "os" in blocked


def test_check_operation_substring_match(profile):
    checker = PermissionChecker(profile)
    assert checker.check_operation("os.system") is False
    assert checker.check_operation("subprocess.run") is False
    assert checker.check_operation("socket.connect") is False


def test_apply_returns_false_when_imports_blocked(profile):
    checker = PermissionChecker(profile)
    assert checker.apply("import os") is False


def test_permission_profile_dataclass():
    profile = PermissionProfile(
        allowed_imports={"math"},
        allowed_builtins={"print"},
        max_execution_time=2.0,
        max_memory_mb=64,
    )
    assert profile.allowed_imports == {"math"}
    assert profile.max_execution_time == 2.0
    assert profile.max_memory_mb == 64


def test_default_allowed_builtins_contains_print():
    assert "print" in PermissionChecker.DEFAULT_ALLOWED_BUILTINS
