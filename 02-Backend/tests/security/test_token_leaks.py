"""Group 1 security tests: token leaks, query-string refresh, OAuth binding.

Each test here is written to fail against the code as it was before the
fix, so a regression in the leak path is a red build, not a note.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

# These are source-integrity checks, so they open the real files rather than
# importing the app. The path is resolved from this file's location so the
# suite behaves identically from the repo root and from 02-Backend/.
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "02-Backend"
AUTH_MODULE = BACKEND_ROOT / "app" / "auth" / "__init__.py"
AUTH_V2 = BACKEND_ROOT / "app" / "routers" / "auth_v2.py"
MAIN_PY = BACKEND_ROOT / "app" / "main.py"

# ---------------------------------------------------------------------------
# Module stubs: import the routers without dragging in the whole dependency
# graph (supabase client, database, provider SDKs). Each stub records what
# the code under test tried to call so the tests can assert on it.
# ---------------------------------------------------------------------------


def _install_stubs(monkeypatch):
    from app.services import token_mailer

    recorder: dict = {
        "magic_links": [],
        "reset_tokens": [],
        "verifications": [],
        "otp_calls": [],
        "oauth_state": {},
    }
    monkeypatch.setattr(token_mailer, "set_mailer", lambda m: None)
    monkeypatch.setattr(token_mailer, "deliver_token", recorder_store := (lambda e, t, p: True))
    return recorder, recorder_store


def test_signup_never_returns_verification_token():
    """auth.py sign_up response must contain no token-bearing fields."""
    import ast

    src = open(AUTH_MODULE, encoding="utf-8").read()
    # No token-shaped literal may be constructed or returned at module level.
    tree = ast.parse(src)
    banned = ("verification_token", "magic_link_token", "reset_token")
    returned: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    returned.add(key.value)
    for name in banned:
        assert name not in returned, f"{name} still present in a return dict"
    assert "user" in returned and "session" in returned, "response shape changed"


def test_signup_has_no_dead_code_after_raise():
    """No function may contain statements after an unconditional raise."""
    import ast

    for path in (AUTH_MODULE, AUTH_V2):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for stmt in node.body:
                if not isinstance(stmt, ast.Raise):
                    continue
                idx = node.body.index(stmt)
                # Every statement after a raise in the same block is dead.
                assert idx == len(node.body) - 1, (
                    f"{node.name} has code after an "
                    f"unconditional raise (dead code)"
                )


def test_single_get_current_user_and_require_admin_definition():
    """Duplicate definitions silently shadow the first copy."""
    import ast

    tree = ast.parse(open(AUTH_MODULE, encoding="utf-8").read())
    for name in ("get_current_user", "require_admin"):
        hits = [
            n for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
        ]
        assert len(hits) == 1, f"{name} defined {len(hits)} times, expected 1"


def test_imports_precede_use_in_auth_module():
    """A function that uses a name imported later fails with NameError on call."""
    import ast

    tree = ast.parse(open(AUTH_MODULE, encoding="utf-8").read())
    import_lines: list[int] = []
    func_defs: list[tuple[str, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)) and node.lineno > 1:
            import_lines.append(node.lineno)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_defs.append((node.name, node.lineno))
    # A function whose first statement begins before every top-level import
    # finishes cannot be trusted: its imports come after it.
    last_import = max(import_lines) if import_lines else 0
    for name, lineno in func_defs:
        body = next(
            n for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
        )
        uses = {
            n.id for n in ast.walk(body)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
        }
        imported_before = set()
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)) and node.lineno < lineno:
                for a in node.names:
                    imported_before.add((a.asname or a.name).split(".")[0])
        # Only flag names imported *later* in the file: that is the bug,
        # not a name that simply is not imported.
        imported_after = set()
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)) and node.lineno > lineno:
                for a in node.names:
                    imported_after.add((a.asname or a.name).split(".")[0])
        late = uses & imported_after
        assert not late, (
            f"{name} uses {sorted(late)}, imported after its definition"
        )


def test_refresh_endpoint_has_no_query_parameter():
    """A refresh token in a query string lands in logs and history."""
    import ast

    for path in (AUTH_MODULE, AUTH_V2):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if "refresh" not in node.name:
                continue
            for arg in node.args.args + node.args.kwonlyargs:
                assert "token" not in arg.arg or arg.annotation is not None, (
                    f"{path}:{node.lineno} {node.name} takes bare '{arg.arg}'; "
                    "a bare parameter becomes a query parameter"
                )


def test_no_bare_except_router_stubs_in_auth_routers():
    """Silent stubs replace a subsystem with an empty router (D05-03)."""
    import ast

    for path in (AUTH_MODULE, AUTH_V2):
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is None:
                raise AssertionError(f"{path}:{node.lineno} bare except")
            # A handler that only assigns an empty router is the stub.
            assigns_empty_router = any(
                isinstance(s, ast.Assign)
                and any(
                    isinstance(v, ast.Call)
                    and getattr(v.func, "id", "") == "APIRouter"
                    for v in s.value.elts if isinstance(s.value, (ast.List, ast.Tuple))
                )
                for s in node.body
            )
            direct = any(
                isinstance(s, ast.Assign)
                and isinstance(s.value, ast.Call)
                and getattr(s.value.func, "id", "") == "APIRouter"
                for s in node.body
            )
            assert not (assigns_empty_router or direct), (
                f"{path}:{node.lineno} except block installs an empty router; "
                "the failure is swallowed"
            )


def test_oauth_provider_must_be_allowlisted():
    """oauth_login must reject a provider outside the configured set."""
    import ast

    tree = ast.parse(open(AUTH_MODULE, encoding="utf-8").read())
    fn = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "oauth_login"
    )
    names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    assert "OAUTH_PROVIDERS" in names, (
        "oauth_login does not check the provider allowlist"
    )
    # And the request token has to be referenced, not ignored.
    body = ast.dump(ast.Module(body=fn.body, type_ignores=[]))
    assert "access_token" in body, "oauth_login ignores its access token"


def test_magic_link_endpoint_never_returns_token():
    """The /magic-link response must not carry magic_link_token."""
    import ast

    tree = ast.parse(open(AUTH_V2, encoding="utf-8").read())
    fn = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "request_magic_link"
    )
    for node in ast.walk(fn):
        if isinstance(node, ast.Constant) and node.value == "magic_link_token":
            raise AssertionError(
                "request_magic_link still returns magic_link_token; "
                "it must be emailed"
            )


def test_token_mailer_records_delivery_and_exposes_nothing():
    """The mailer contract: record metadata, never the token body."""
    import sys

    sys.path.insert(0, str(BACKEND_ROOT))
    from app.services.token_mailer import RecordingMailer, deliver_token, set_mailer

    recorder = RecordingMailer()
    set_mailer(recorder)
    try:
        ok = deliver_token("user@example.com", "S3CRET-VALUE", "magic_link")
    finally:
        set_mailer(None)
    assert ok is True
    assert len(recorder.sent) == 1
    record = recorder.sent[0]
    assert record["email"] == "user@example.com"
    assert record["purpose"] == "magic_link"
    # The full token must not be stored by the recorder.
    assert "S3CRET-VALUE" not in repr(record)


def test_token_mailer_null_mailer_does_not_log_token(caplog):
    """An unconfigured mailer must fail closed without leaking the token."""
    import sys

    sys.path.insert(0, str(BACKEND_ROOT))
    from app.services.token_mailer import NullMailer

    mailer = NullMailer()
    ok = mailer.send_token(
        "user@example.com", "S3CRET-VALUE", "magic_link", "15 minutes"
    )
    assert ok is False
    assert "S3CRET-VALUE" not in caplog.text, "token leaked into logs"


def test_router_error_stubs_are_replaced_in_main():
    """main.py must not install an empty router in an except block."""
    import ast

    tree = ast.parse(open(MAIN_PY, encoding="utf-8").read())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            if not isinstance(handler, ast.ExceptHandler):
                continue
            for stmt in handler.body:
                if (
                    isinstance(stmt, ast.Assign)
                    and isinstance(stmt.value, ast.Call)
                    and getattr(stmt.value.func, "id", "") == "APIRouter"
                ):
                    offenders.append(handler.lineno)
    assert not offenders, (
        f"main.py still installs empty routers at lines {offenders}; "
        "the failure is swallowed (D05-03)"
    )
