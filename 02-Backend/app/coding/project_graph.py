"""Project graph: call graph, dependency graph, whole-project understanding."""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any


logger = logging.getLogger(__name__)


class ProjectGraph:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.nodes: dict[str, dict[str, Any]] = {}
        self.call_edges: dict[str, set[str]] = defaultdict(set)
        self.file_imports: dict[str, list[str]] = defaultdict(list)
        self.symbol_to_file: dict[str, str] = {}

    def build(self, index: Any) -> dict[str, Any]:
        for rel_path, file_info in index.files.items():
            self._ingest_file(rel_path, file_info)
        return {
            "nodes": len(self.nodes),
            "call_edges": sum(len(v) for v in self.call_edges.values()),
            "import_edges": sum(len(v) for v in self.file_imports.values()),
        }

    def _ingest_file(self, rel_path: str, file_info: dict[str, Any]) -> None:
        lang = file_info.get("language")
        if lang is None:
            return
        self.nodes[rel_path] = {
            "path": rel_path,
            "language": lang,
            "symbols": file_info.get("symbols", []),
            "size": file_info.get("size", 0),
        }
        for sym in file_info.get("symbols", []):
            name = sym.get("name")
            if name:
                self.symbol_to_file[name] = rel_path
        try:
            full_path = os.path.join(self.repo_path, rel_path)
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.file_imports[rel_path] = self._extract_imports(content, lang)
            if lang == "python":
                self._build_call_graph_python(rel_path, content)
        except Exception as exc:
            logger.debug("Project graph ingest failed for %s: %s", rel_path, exc)

    def _extract_imports(self, content: str, language: str) -> list[str]:
        imports: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(stripped.split("#")[0].strip())
            elif stripped.startswith("require("):
                imports.append(stripped)
            elif stripped.startswith("use ") or stripped.startswith("include "):
                imports.append(stripped)
            elif stripped.startswith("@import") or stripped.startswith("@include"):
                imports.append(stripped)
        return imports

    def _build_call_graph_python(self, rel_path: str, content: str) -> None:
        try:
            import ast

            tree = ast.parse(content)
            defined = {node.name: node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    name = None
                    if isinstance(func, ast.Name):
                        name = func.id
                    elif isinstance(func, ast.Attribute):
                        if isinstance(func.value, ast.Name):
                            name = f"{func.value.id}.{func.attr}"
                    if name and name in defined:
                        caller = defined.get(name)
                        if isinstance(caller, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            self.call_edges[caller.name].add(name)
        except Exception:
            pass

    def get_dependents(self, symbol_name: str) -> list[str]:
        callers = set()
        for caller, callees in self.call_edges.items():
            if symbol_name in callees:
                callers.add(caller)
        return list(callers)

    def get_dependencies(self, symbol_name: str) -> set[str]:
        return self.call_edges.get(symbol_name, set())

    def get_file_dependencies(self, rel_path: str) -> list[str]:
        return self.file_imports.get(rel_path, [])

    def get_symbol_location(self, name: str) -> str | None:
        return self.symbol_to_file.get(name)

    def get_architecture_summary(self) -> dict[str, Any]:
        languages: dict[str, int] = defaultdict(int)
        for node in self.nodes.values():
            languages[node.get("language", "unknown")] += 1
        return {
            "total_files": len(self.nodes),
            "languages": dict(languages),
            "top_symbols": sorted(
                [(name, len(self.get_dependents(name)) + len(self.get_dependencies(name)))
                 for name in list(self.symbol_to_file.keys())[:200]],
                key=lambda x: x[1],
                reverse=True,
            )[:50],
        }
