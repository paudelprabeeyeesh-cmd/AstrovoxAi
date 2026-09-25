#!/usr/bin/env python3
"""
Complexity Analyzer - Measures cyclomatic complexity and identifies complex functions.
"""
import ast
import json
import sys
from pathlib import Path
from typing import Any

Path("code-quality-reports").mkdir(exist_ok=True)


def complexity(node: ast.AST) -> int:
    return sum(
        1
        for child in ast.walk(node)
        if isinstance(child, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler))
    )


def analyze_file(path: Path) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            c = complexity(node)
            if c > 10:
                results.append({
                    "file": str(path),
                    "function": node.name,
                    "line": node.lineno,
                    "complexity": c,
                })
    return results


def scan_directory(base: Path) -> list[dict[str, Any]]:
    results = []
    for py_file in sorted(base.rglob("*.py")):
        results.extend(analyze_file(py_file))
    results.sort(key=lambda x: x["complexity"], reverse=True)
    return results[:50]


if __name__ == "__main__":
    target = Path("02-Backend/app") if Path("02-Backend/app").exists() else Path(".")
    results = scan_directory(target)
    Path("code-quality-reports/complexity-report.json").write_text(json.dumps(results, indent=2))
    if results:
        print(f"Found {len(results)} complex functions (complexity > 10)")
        sys.exit(1)
    print("No overly complex functions found")
    sys.exit(0)
