"""Dependency analyzer."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

IMPORT_PATTERNS = {
    "python": re.compile(r"^(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.M),
    "javascript": re.compile(r"^(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))", re.M),
    "typescript": re.compile(r"^(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))", re.M),
    "go": re.compile(r"^import\s+(?:\"([^\"]+)\")", re.M),
    "rust": re.compile(r"^(?:use\s+([\w:]+)|extern\s+crate\s+([\w]+))", re.M),
}


class DependencyAnalyzer:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def analyze(self, index: Any) -> dict[str, Any]:
        deps: dict[str, list[str]] = {}
        for rel, entry in index.files.items():
            pattern = IMPORT_PATTERNS.get(entry.language)
            if not pattern:
                continue
            try:
                with open(entry.path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            matches = pattern.findall(content)
            imports: list[str] = []
            for m in matches:
                imports.append(next((x for x in m if x), ""))
            deps[rel] = sorted({i for i in imports if i})
        return {"files": len(deps), "dependencies": deps, "circular_dependencies": self._find_cycles(deps)}

    def _find_cycles(self, deps: dict[str, list[str]]) -> list[list[str]]:
        graph: dict[str, list[str]] = {k: v for k, v in deps.items()}
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    idx = path.index(neighbor)
                    cycles.append(path[idx:] + [neighbor])
            path.pop()
            rec_stack.remove(node)
            return False

        for node in list(graph.keys()):
            if node not in visited:
                dfs(node)
        return cycles
