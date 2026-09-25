#!/usr/bin/env python3
"""
Circular Dependency Detector - Finds circular imports in Python and TS/JS.
"""
import ast
import json
import sys
from pathlib import Path
from typing import Any


def find_py_circular(base: Path) -> list[dict[str, Any]]:
    graph: dict[str, set[str]] = {}
    for py_file in sorted(base.rglob("*.py")):
        rel = str(py_file.relative_to(base))
        graph.setdefault(rel, set())
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module.replace(".", "/")
                mod_file = base / f"{mod}.py"
                if mod_file.exists():
                    graph[rel].add(str(mod_file.relative_to(base)))
    return _find_cycles(graph)


def find_ts_circular(base: Path) -> list[dict[str, Any]]:
    graph: dict[str, set[str]] = {}
    for ts_file in sorted(base.rglob("*.ts")):
        rel = str(ts_file.relative_to(base))
        graph.setdefault(rel, set())
        text = ts_file.read_text()
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("import "):
                if " from " in line:
                    parts = line.split(" from ")
                    if len(parts) == 2:
                        mod = parts[1].strip().rstrip(";").strip("\"'")
                        if mod.startswith("."):
                            base_dir = ts_file.parent
                            target = (base_dir / mod).resolve()
                            candidates = [
                                target.with_suffix(".ts"),
                                target.with_suffix(".tsx"),
                                target / "index.ts",
                                target / "index.tsx",
                            ]
                            for c in candidates:
                                try:
                                    c.relative_to(base)
                                    graph[rel].add(str(c.relative_to(base)))
                                except ValueError:
                                    pass
    return _find_cycles(graph)


def _find_cycles(graph: dict[str, set[str]]) -> list[dict[str, Any]]:
    cycles: list[dict[str, Any]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def dfs(node: str, path: list[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in sorted(graph.get(node, [])):
            if neighbor in rec_stack:
                idx = path.index(neighbor)
                cycles.append({"cycle": path[idx:] + [neighbor]})
            elif neighbor not in visited:
                dfs(neighbor, path)
        path.pop()
        rec_stack.discard(node)

    for node in sorted(graph):
        if node not in visited:
            dfs(node, [])
    return cycles


if __name__ == "__main__":
    results = {
        "python": find_py_circular(Path("02-Backend/app")),
        "typescript": find_ts_circular(Path(".")),
    }
    Path("code-quality-reports/circular-deps-report.json").write_text(json.dumps(results, indent=2))
    total = len(results["python"]) + len(results["typescript"])
    if total:
        print(f"Found {total} circular dependency cycles")
        sys.exit(1)
    print("No circular dependencies found")
    sys.exit(0)
