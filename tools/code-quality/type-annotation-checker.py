#!/usr/bin/env python3
"""
Type Annotation Checker - Reports missing type annotations in Python code.
"""
import ast
import json
import sys
from pathlib import Path
from typing import Any

Path("code-quality-reports").mkdir(exist_ok=True)


def check_annotations(node: ast.AST, path: Path) -> list[dict[str, Any]]:
    issues = []
    for child in ast.walk(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if child.returns is None:
                issues.append({
                    "file": str(path),
                    "function": child.name,
                    "line": child.lineno,
                    "issue": "missing return type annotation",
                })
            if child.args.args and not any(
                child.args.args, getattr(child.args, "posonlyargs", [])
            ):
                for arg in child.args.args:
                    if arg.arg == "self":
                        continue
                    if arg.annotation is None:
                        issues.append({
                            "file": str(path),
                            "function": f"{child.name}({arg.arg})",
                            "line": child.lineno,
                            "issue": f"missing parameter type annotation: {arg.arg}",
                        })
    return issues


def scan_directory(base: Path) -> list[dict[str, Any]]:
    all_issues = []
    for py_file in sorted(base.rglob("*.py")):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        all_issues.extend(check_annotations(tree, py_file))
    return all_issues[:100]


if __name__ == "__main__":
    target = Path("02-Backend/app") if Path("02-Backend/app").exists() else Path(".")
    issues = scan_directory(target)
    Path("code-quality-reports/type-annotation-report.json").write_text(json.dumps(issues, indent=2))
    if issues:
        print(f"Found {len(issues)} missing type annotations")
        sys.exit(1)
    print("All functions have type annotations")
    sys.exit(0)
