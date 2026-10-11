#!/usr/bin/env python
"""Fail if product code imports experimental code.

D01-11: product code must have no dependency on experimental modules.

The live module set is the set of top-level packages that `02-Backend/app/`
actually imports (see docs/MODULE_INVENTORY.md). This script walks every
module under the live set and fails when one of them imports a module from the
experimental set, so a new dependency cannot be introduced silently.

Usage:
    python tools/check_live_imports.py

Exit codes:
    0  no violations
    1  at least one violation, or the live set could not be determined
"""

from __future__ import annotations

import ast
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(REPO_ROOT, "02-Backend")
APP = os.path.join(BACKEND, "app")

# Top-level modules that are allowed to be imported by product code.
LIVE_EXTRA = {
    "app",
    "routes",
    "api_gateway",
    "sandboxing",
    "database",
    "retrieval",
    "memory_persistence",
}

# Standard library and third-party modules are not app modules; everything
# else that resolves to a sibling of `app/` is treated as experimental.
EXPERIMENTAL_ALLOWLIST = set()  # keep empty; explicit violations fail


def top_level_names() -> set[str]:
    """Top-level packages/modules that exist under 02-Backend."""
    names = set()
    try:
        for name in os.listdir(BACKEND):
            if name.startswith(".") or name == "__pycache__":
                continue
            path = os.path.join(BACKEND, name)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "__init__.py")):
                names.add(name)
            elif os.path.isfile(path) and name.endswith(".py"):
                names.add(name[: -len(".py")])
    except OSError as exc:  # pragma: no cover - unreadable checkout
        print(f"error: cannot list {BACKEND}: {exc}", file=sys.stderr)
        raise
    return names


def imported_module(node: ast.AST) -> set[str]:
    """Top-level names imported by an import statement."""
    found: set[str] = set()
    if isinstance(node, ast.Import):
        for alias in node.names:
            found.add(alias.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        if node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def live_roots() -> list[str]:
    """Directories whose code is considered product code."""
    roots = [APP]
    for name in sorted(LIVE_EXTRA):
        path = os.path.join(BACKEND, name)
        if name != "app" and os.path.isdir(path):
            roots.append(path)
    return roots


def check() -> int:
    all_names = top_level_names()
    live = LIVE_EXTRA | {"app"}
    experimental = all_names - live

    violations: list[str] = []
    scanned = 0

    for root in live_roots():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(dirpath, filename)
                try:
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        tree = ast.parse(handle.read(), filename=path)
                except (OSError, SyntaxError):
                    continue
                scanned += 1
                for node in ast.walk(tree):
                    for name in imported_module(node):
                        if name in experimental and name not in EXPERIMENTAL_ALLOWLIST:
                            violations.append(
                                f"{os.path.relpath(path, REPO_ROOT)} imports experimental module '{name}'"
                            )

    print(f"scanned {scanned} product modules across {len(live_roots())} live roots")
    print(f"experimental modules tracked: {len(experimental)}")

    if violations:
        print("\nviolations:", file=sys.stderr)
        for line in sorted(set(violations)):
            print(f"  {line}", file=sys.stderr)
        return 1

    print("ok: product code imports no experimental module")
    return 0


def main() -> int:
    try:
        return check()
    except OSError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
