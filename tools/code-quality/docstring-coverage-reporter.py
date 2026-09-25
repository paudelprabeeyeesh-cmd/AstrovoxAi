#!/usr/bin/env python3
"""
Docstring Coverage Reporter - Reports missing docstrings and coverage percentage.
"""
import ast
import json
import sys
from pathlib import Path
from typing import Any


def check_docstrings(node: ast.AST, path: Path) -> tuple[int, int, list[dict[str, Any]]]:
    total = 0
    covered = 0
    missing: list[dict[str, Any]] = []
    for child in ast.walk(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            total += 1
            docstring = ast.get_docstring(child)
            if docstring:
                covered += 1
            else:
                kind = "class" if isinstance(child, ast.ClassDef) else "function"
                missing.append({
                    "file": str(path),
                    "kind": kind,
                    "name": child.name,
                    "line": child.lineno,
                })
    return total, covered, missing


def scan_directory(base: Path) -> dict[str, Any]:
    total = 0
    covered = 0
    all_missing: list[dict[str, Any]] = []
    for py_file in sorted(base.rglob("*.py")):
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        t, c, missing = check_docstrings(tree, py_file)
        total += t
        covered += c
        all_missing.extend(missing)
    pct = round((covered / total) * 100, 2) if total else 0.0
    return {"total": total, "covered": covered, "coverage_pct": pct, "missing": all_missing[:50]}


if __name__ == "__main__":
    target = Path("02-Backend/app") if Path("02-Backend/app").exists() else Path(".")
    report = scan_directory(target)
    Path("code-quality-reports/docstring-coverage-report.json").write_text(json.dumps(report, indent=2))
    print(f"Docstring coverage: {report['coverage_pct']}% ({report['covered']}/{report['total']})")
    if report["missing"]:
        print(f"Found {len(report['missing'])} missing docstrings")
        sys.exit(1)
    sys.exit(0)
