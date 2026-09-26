"""Dependency analysis for code repositories."""

from __future__ import annotations

import ast
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def analyze_file(self, file_path: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        ext = os.path.splitext(file_path)[1].lower()
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc)}
        if ext == ".py":
            return self._analyze_python(content, file_path)
        return self._analyze_generic(content, file_path)

    def analyze_repo(self, index: Any) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for rel_path in index.files:
            results[rel_path] = self.analyze_file(rel_path)
        circular = self._detect_circular(results)
        unused = self._detect_unused(results, index)
        return {"files": results, "circular_dependencies": circular, "potentially_unused": unused}

    def _analyze_python(self, content: str, file_path: str) -> dict[str, Any]:
        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            return {"file": file_path, "error": f"syntax error: {exc}", "imports": [], "defined": []}
        imports: list[dict[str, Any]] = []
        defined: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({"type": "import", "module": alias.name, "alias": alias.asname, "line": node.lineno})
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({
                        "type": "from",
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.append(node.name)
        return {"file": file_path, "imports": imports, "defined": defined}

    def _analyze_generic(self, content: str, file_path: str) -> dict[str, Any]:
        imports: list[dict[str, Any]] = []
        for lineno, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append({"type": "import", "line": stripped, "line_no": lineno})
            elif stripped.startswith("require("):
                imports.append({"type": "require", "line": stripped, "line_no": lineno})
            elif stripped.startswith("use ") or stripped.startswith("include "):
                imports.append({"type": "use", "line": stripped, "line_no": lineno})
        return {"file": file_path, "imports": imports, "defined": []}

    def _detect_circular(self, results: dict[str, Any]) -> list[list[str]]:
        graph: dict[str, set[str]] = {k: set() for k in results}
        for file_path, data in results.items():
            if not isinstance(data, dict):
                continue
            for imp in data.get("imports", []):
                mod = imp.get("module") or imp.get("line", "")
                base = mod.split(".")[0] if mod else ""
                if base and base in graph:
                    graph[file_path].add(base)
        cycles: list[list[str]] = []
        visited = set()
        for start in graph:
            if start in visited:
                continue
            path: list[str] = []
            seen: set[str] = set()
            node = start
            while node and node not in seen:
                seen.add(node)
                path.append(node)
                visited.add(node)
                neighbors = [n for n in graph.get(node, set()) if n in graph]
                if not neighbors:
                    break
                node = neighbors[0]
            if node and node in seen:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
        return cycles

    def _detect_unused(self, results: dict[str, Any], index: Any) -> list[str]:
        defined: set[str] = set()
        used: set[str] = set()
        for file_path, data in results.items():
            if not isinstance(data, dict):
                continue
            for sym in data.get("defined", []):
                defined.add(sym)
            for imp in data.get("imports", []):
                name = imp.get("name") or imp.get("module", "")
                if name:
                    used.add(name.split(".")[-1])
        return sorted(list(defined - used))[:100]
