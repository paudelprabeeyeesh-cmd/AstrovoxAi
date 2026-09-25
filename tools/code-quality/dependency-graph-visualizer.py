#!/usr/bin/env python3
"""
Dependency Graph Visualizer - Generates a dependency graph of the codebase.
"""
import ast
import json
import sys
from pathlib import Path
from typing import Any

Path("code-quality-reports").mkdir(exist_ok=True)


def extract_imports(path: Path, base: Path) -> list[str]:
    deps = []
    try:
        tree = ast.parse(path.read_text())
    except Exception:
        return deps
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module.replace(".", "/")
            mod_file = base / f"{mod}.py"
            if mod_file.exists():
                try:
                    deps.append(str(mod_file.relative_to(base)))
                except ValueError:
                    pass
    return deps


def build_graph(base: Path) -> dict[str, Any]:
    nodes = []
    edges = []
    files = sorted(base.rglob("*.py"))
    for py_file in files:
        try:
            rel = str(py_file.relative_to(base))
        except ValueError:
            continue
        nodes.append({"id": rel, "type": "file"})
        deps = extract_imports(py_file, base)
        for dep in deps:
            edges.append({"source": rel, "target": dep})
    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    target = Path("02-Backend/app") if Path("02-Backend/app").exists() else Path(".")
    graph = build_graph(target)
    Path("code-quality-reports/dependency-graph.json").write_text(json.dumps(graph, indent=2))
    print(f"Dependency graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
    sys.exit(0)
