"""Project graph for whole-project understanding."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class ProjectGraph:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, str]] = []

    def add_file(self, path: str, language: str) -> None:
        self.nodes[path] = {"type": "file", "language": language}

    def add_symbol(self, path: str, name: str, kind: str) -> None:
        node_id = f"{path}:{name}"
        self.nodes[node_id] = {"type": "symbol", "name": name, "kind": kind, "file": path}
        self.edges.append({"from": node_id, "to": path, "type": "defined_in"})

    def add_dependency(self, src: str, dst: str, dep_type: str = "imports") -> None:
        self.edges.append({"from": src, "to": dst, "type": dep_type})

    def detect_cycles(self) -> list[list[str]]:
        graph: dict[str, list[str]] = {}
        for edge in self.edges:
            graph.setdefault(edge["from"], []).append(edge["to"])
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

    def topological_order(self) -> list[str]:
        graph: dict[str, list[str]] = {}
        in_degree: dict[str, int] = {}
        for edge in self.edges:
            graph.setdefault(edge["from"], []).append(edge["to"])
            in_degree.setdefault(edge["to"], 0)
            in_degree[edge["from"]] = in_degree.get(edge["from"], 0)
            in_degree[edge["to"]] = in_degree.get(edge["to"], 0) + 1
        queue = [n for n in in_degree if in_degree[n] == 0]
        order: list[str] = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return order

    def summarize(self) -> dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "cycles": len(self.detect_cycles()),
            "languages": list({n.get("language") for n in self.nodes.values() if n.get("language")}),
        }
