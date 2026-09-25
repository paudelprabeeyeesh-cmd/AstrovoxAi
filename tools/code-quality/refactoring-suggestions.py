#!/usr/bin/env python3
"""
Automated Refactoring Suggestions - Suggests improvements based on code patterns.
"""
import ast
import json
import sys
from pathlib import Path
from typing import Any


SUGGESTIONS = []


def suggest_long_functions(path: Path, tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = node.end_lineno or node.lineno
            if end - start > 50:
                SUGGESTIONS.append({
                    "file": str(path),
                    "line": node.lineno,
                    "function": node.name,
                    "suggestion": f"Function '{node.name}' is {end - start} lines. Consider splitting into smaller functions.",
                    "priority": "medium",
                })


def suggest_deep_nesting(path: Path, tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            depth = 0
            max_depth = 0
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    depth += 1
                    max_depth = max(max_depth, depth)
            if max_depth > 4:
                SUGGESTIONS.append({
                    "file": str(path),
                    "line": node.lineno,
                    "function": node.name,
                    "suggestion": f"Function '{node.name}' has nesting depth {max_depth}. Consider extracting inner logic.",
                    "priority": "medium",
                })


def suggest_many_arguments(path: Path, tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = len(node.args.args)
            if args > 6:
                SUGGESTIONS.append({
                    "file": str(path),
                    "line": node.lineno,
                    "function": node.name,
                    "suggestion": f"Function '{node.name}' has {args} parameters. Consider using a dataclass or kwargs.",
                    "priority": "low",
                })


def scan_directory(base: Path) -> list[dict[str, Any]]:
    global SUGGESTIONS
    SUGGESTIONS = []
    for py_file in sorted(base.rglob("*.py")):
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        suggest_long_functions(py_file, tree)
        suggest_deep_nesting(py_file, tree)
        suggest_many_arguments(py_file, tree)
    return SUGGESTIONS[:100]


if __name__ == "__main__":
    target = Path("02-Backend/app") if Path("02-Backend/app").exists() else Path(".")
    suggestions = scan_directory(target)
    Path("code-quality-reports/refactoring-suggestions-report.json").write_text(json.dumps(suggestions, indent=2))
    if suggestions:
        print(f"Generated {len(suggestions)} refactoring suggestions")
    else:
        print("No refactoring suggestions")
    sys.exit(0)
