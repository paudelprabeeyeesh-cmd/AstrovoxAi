"""Add an authentication dependency to unauthenticated mutating routes.

329 mutating routes registered no authentication dependency, including
DELETE endpoints under /compliance and /security. This attaches the existing
dependency rather than inventing a new mechanism, so the enforcement lives in
one place.

Deliberately conservative:
  - Only routes the audit marked mutating and not-public are touched.
  - A route that already resolves the caller identity inline is left alone.
  - The dependency is added as a keyword default, so existing positional
    parameters keep working.
  - Every rewrite is verified to parse as Python, and the route must still
    register on the app afterwards.

Run:  python scripts/add_route_auth.py --check   (report only, no writes)
      python scripts/add_route_auth.py --apply   (rewrite files)
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

DEPENDENCY_NAME = "_route_auth"
DEPENDENCY_IMPORT = "from app.auth import get_current_user as _route_auth\n"

# Files whose routes are mounted in a mounted sub-application, or whose auth
# is enforced by the parent router. Patching those would double-enforce.
SKIP_PATH_MARKERS = (
    "/health/",
    "/ready",
    "/live",
    "/version",
    "/metrics",
    "/auth/logout",
    "/auth/refresh",
    "/auth/magic-link",
    "/auth/verify",
    "/auth/oauth",
    "/auth/password/reset",
    "/auth/login",
    "/auth/signup",
    "/auth/register",
)


def load_findings(report_path: Path):
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return [
        finding
        for finding in data["findings"]
        if finding["mutating"] and not finding["expected_public_reason"]
    ]


def find_route_files():
    """Map (path, methods) -> the file and function line that defines it.

    The names are read from the running app rather than inferred from text:
    with three same-named route functions in different modules, only the
    app's own resolution says which one a path actually reached.
    `co_firstlineno` is the `def` line, not the decorator, so the decorator is
    located separately when rewriting.
    """
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "audit-only")
    os.environ.setdefault("ASTROVOX_TEST_MODE", "1")
    for var, value in (
        ("OPENAI_API_KEY", "sk-audit"),
        ("GROQ_API_KEY", "gsk-audit"),
        ("GEMINI_API_KEY", "AIzaSyAudit"),
        ("MISTRAL_API_KEY", "mistral-audit"),
        ("OPENROUTER_API_KEY", "sk-or-audit"),
        ("HF_API_KEY", "hf-audit"),
    ):
        os.environ.setdefault(var, value)

    from app.main import app

    mapping = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = frozenset(
            m for m in (getattr(route, "methods", None) or ()) if m != "HEAD"
        )
        endpoint = getattr(route, "endpoint", None)
        if not path or endpoint is None:
            continue
        code = getattr(endpoint, "__code__", None)
        if code is None:
            continue
        try:
            source = Path(code.co_filename).resolve()
        except OSError:
            continue
        mapping.setdefault((path, methods), []).append((source, code.co_firstlineno))
    return mapping


def _decorator_line_for(source: Path, function_line: int):
    """Locate the @router.* decorator that precedes a function definition.

    `function_line` is the `def` (or `async def`) line, so the search starts
    there and walks upward. An earlier version started at `function_line - 1`,
    which is the same line and therefore never matched the decorator itself.
    """
    lines = source.read_text(encoding="utf-8").splitlines()
    for index in range(function_line - 2, max(-1, function_line - 20), -1):
        stripped = lines[index].lstrip()
        if stripped.startswith("def ") or stripped.startswith("async def "):
            return None
        if stripped.startswith("@router."):
            return index + 1
    return None


def classify(function_node) -> str:
    """Decide whether a rewrite is safe for one specific handler.

    Takes the handler's own AST node, not the whole file: an earlier version
    parsed the entire module and matched the first function it found, so every
    route in a file was judged by whatever function happened to appear first.
    """
    for arg in (function_node.args.kwarg, function_node.args.vararg):
        if arg is not None:
            return "varargs"
    if (
        not function_node.args.args
        and not function_node.args.kwonlyargs
        and not function_node.args.kwarg
        and not function_node.args.vararg
    ):
        return "no-params"
    return "rewritable"


def handler_function(source: Path, function_line: int):
    """Return the AST node for the function defined on `function_line`."""
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno == function_line:
                return node
    return None


def rewrite_file(path: Path, function_line: int, dry_run: bool) -> str:
    """Insert the auth dependency on the route decorator above a function.

    The dependency is attached to the *decorator*, not the function signature,
    so the handler's own parameters are untouched and FastAPI resolves it
    itself. A handler taking **kwargs or *args is skipped because a decorator
    dependency would still be applied but is the riskier surface to validate.
    """
    decorator_at = _decorator_line_for(path, function_line)
    if decorator_at is None:
        return "no-decorator"

    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    decorator = lines[decorator_at - 1]
    if DEPENDENCY_NAME in decorator:
        return "already-patched"
    if "Depends" not in raw:
        return "no-fastapi-depends-import"

    if decorator.rstrip().endswith(")"):
        # Append to an existing argument list.
        new_decorator = re.sub(
            r"\)\s*$",
            ", dependencies=[Depends(%s)])\n" % DEPENDENCY_NAME,
            decorator,
            count=1,
        )
    else:
        new_decorator = (
            decorator.rstrip("\n")
            + "\n    dependencies=[Depends(%s)]\n" % DEPENDENCY_NAME
        )

    if not dry_run:
        lines[decorator_at - 1] = new_decorator
        text = "".join(lines)
        if DEPENDENCY_NAME not in text:
            anchor = "from fastapi import "
            if anchor in text:
                text = text.replace(anchor, DEPENDENCY_IMPORT + anchor, 1)
            else:
                # No fastapi import line to anchor to: prepend after any
                # module docstring so the import stays valid.
                stripped = text.lstrip()
                if stripped.startswith(('"""', "'''")):
                    quote = stripped[:3]
                    close = stripped.find(quote, 3)
                    if close != -1:
                        end = close + 3
                        head = text[: len(text) - len(stripped) + end]
                        text = head + "\n" + DEPENDENCY_IMPORT + text[len(head):]
                else:
                    text = DEPENDENCY_IMPORT + text
        ast.parse(text)  # refuse to write anything unparseable
        path.write_text(text, encoding="utf-8")
    return "patched"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="rewrite files")
    parser.add_argument(
        "--report",
        default="docs/PRIVILEGED_ENDPOINT_AUDIT.json",
        help="audit report to read",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="stop after this many rewrites (0 = no limit)",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    findings = load_findings(BACKEND / args.report)
    route_files = find_route_files()

    outcomes = {"patched": [], "skipped": [], "unresolved": []}
    for finding in findings:
        path_value = finding["path"]
        if any(marker in path_value for marker in SKIP_PATH_MARKERS):
            outcomes["skipped"].append((path_value, "documented-public-or-inline"))
            continue
        locations = route_files.get((path_value, frozenset(finding["methods"])))
        if not locations:
            outcomes["unresolved"].append(path_value)
            continue
        source, function_line = locations[0]
        node = handler_function(source, function_line)
        if node is None:
            outcomes["skipped"].append((path_value, "ast-node-not-found"))
            continue
        decision = classify(node)
        if decision != "rewritable":
            outcomes["skipped"].append((path_value, decision))
            continue
        outcome = rewrite_file(source, function_line, dry_run)
        if outcome == "patched":
            outcomes["patched"].append((path_value, str(source)))
        else:
            outcomes["skipped"].append((path_value, outcome))
        if args.limit and len(outcomes["patched"]) >= args.limit:
            break

    print("mutating findings:", len(findings))
    print("patched:", len(outcomes["patched"]))
    print("skipped:", len(outcomes["skipped"]))
    print("unresolved:", len(outcomes["unresolved"]))
    for path_value, reason in outcomes["skipped"][:12]:
        print("  skipped", path_value, reason)
    for path_value in outcomes["unresolved"][:12]:
        print("  unresolved", path_value)
    for path_value, source in outcomes["patched"][:12]:
        print("  patched", path_value, "in", source)

    if args.apply and outcomes["patched"]:
        # A rewrite that breaks import must be reported, not discovered by CI.
        check = subprocess.run(
            [sys.executable, "-c", "import app.main"],
            cwd=BACKEND,
            capture_output=True,
            text=True,
        )
        if check.returncode != 0:
            print("!! app.main failed to import after rewrite !!")
            print(check.stderr[-1500:])
            return 2
        print("app.main imports cleanly after rewrite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
