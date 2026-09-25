#!/usr/bin/env python3
"""
API Breaking Change Detector - Detects breaking changes in API contracts.
"""
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


def extract_routes_from_file(path: Path) -> list[dict[str, Any]]:
    routes = []
    try:
        text = path.read_text()
        tree = ast.parse(text)
    except Exception:
        return routes
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in ("post", "get", "put", "delete", "patch"):
                routes.append({
                    "file": str(path),
                    "method": func.attr.upper(),
                    "line": node.lineno,
                    "decorator": ast.unparse(node) if hasattr(ast, "unparse") else "",
                })
    return routes


def extract_routes_from_dir(base: Path) -> list[dict[str, Any]]:
    routes = []
    for py_file in sorted(base.rglob("*.py")):
        routes.extend(extract_routes_from_file(py_file))
    return routes


def compare_baseline(current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline_file = Path("code-quality-reports/api-baseline.json")
    if not baseline_file.exists():
        baseline_file.write_text(json.dumps(current, indent=2))
        return []
    try:
        baseline = json.loads(baseline_file.read_text())
    except Exception:
        baseline = []
    baseline_methods = {(r["method"], r["file"]) for r in baseline}
    current_methods = {(r["method"], r["file"]) for r in current}
    removed = baseline_methods - current_methods
    return [{"removed_route": {"method": m, "file": f}} for m, f in removed]


if __name__ == "__main__":
    base = Path("02-Backend/app") if Path("02-Backend/app").exists() else Path(".")
    routes = extract_routes_from_dir(base)
    Path("code-quality-reports/api-current.json").write_text(json.dumps(routes, indent=2))
    breaking = compare_baseline(routes)
    Path("code-quality-reports/api-breaking-changes-report.json").write_text(json.dumps(breaking, indent=2))
    if breaking:
        print(f"Found {len(breaking)} potential API breaking changes")
        sys.exit(1)
    print("No API breaking changes detected")
    sys.exit(0)
