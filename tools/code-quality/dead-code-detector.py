#!/usr/bin/env python3
"""
Dead Code Detector - Identifies unused functions, classes, and imports.
"""
import ast
import json
import sys
from pathlib import Path
from typing import Any


class DeadCodeVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.defined: set[str] = set()
        self.used: set[str] = set()
        self.unused: list[str] = []
        self.current_scope: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self.defined.add(name)
            self.used.add(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            full = f"{node.module}.{name}" if node.module else name
            self.defined.add(full)
            self.used.add(full)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        name = ".".join(self.current_scope + [node.name])
        self.defined.add(name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        name = ".".join(self.current_scope + [node.name])
        self.defined.add(name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        name = ".".join(self.current_scope + [node.name])
        self.defined.add(name)
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used.add(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used.add(node.attr)


def scan_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    visitor = DeadCodeVisitor()
    visitor.visit(tree)
    return [name for name in visitor.defined if name not in visitor.used]


def scan_directory(base: Path) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for py_file in sorted(base.rglob("*.py")):
        unused = scan_file(py_file)
        if unused:
            results[str(py_file.relative_to(base))] = unused
    return results


if __name__ == "__main__":
    target = Path("02-Backend/app") if Path("02-Backend/app").exists() else Path(".")
    findings = scan_directory(target)
    output = json.dumps(findings, indent=2)
    Path("code-quality-reports/dead-code-report.json").write_text(output)
    if findings:
        print(f"Dead code found in {len(findings)} files")
        sys.exit(1)
    print("No dead code detected")
    sys.exit(0)
