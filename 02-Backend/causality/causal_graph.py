from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CausalNode:
    id: str
    variable: str
    observed: bool = True
    value: Optional[float] = None


@dataclass
class CausalEdge:
    source: str
    target: str
    strength: float = 1.0
    sign: str = "positive"


class CausalGraph:
    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge] = []
        self._outgoing: Dict[str, List[str]] = {}
        self._incoming: Dict[str, List[str]] = {}

    def add_node(self, node: CausalNode) -> None:
        self.nodes[node.id] = node
        self._outgoing.setdefault(node.id, [])
        self._incoming.setdefault(node.id, [])

    def add_edge(self, edge: CausalEdge) -> None:
        self.edges.append(edge)
        self._outgoing.setdefault(edge.source, []).append(edge.target)
        self._incoming.setdefault(edge.target, []).append(edge.source)

    def remove_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            return
        del self.nodes[node_id]
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
        self._outgoing.pop(node_id, None)
        self._incoming.pop(node_id, None)
        for src in self._outgoing:
            self._outgoing[src] = [n for n in self._outgoing[src] if n != node_id]
        for tgt in self._incoming:
            self._incoming[tgt] = [n for n in self._incoming[tgt] if n != node_id]

    def get_neighbors(self, node_id: str) -> List[str]:
        return list(self._outgoing.get(node_id, []))

    def get_descendants(self, node_id: str) -> Set[str]:
        visited: Set[str] = set()
        queue = deque(self.get_neighbors(node_id))
        while queue:
            current = queue.popleft()
            if current not in visited:
                visited.add(current)
                queue.extend(self._outgoing.get(current, []))
        return visited

    def get_ancestors(self, node_id: str) -> Set[str]:
        visited: Set[str] = set()
        queue = deque(self._incoming.get(node_id, []))
        while queue:
            current = queue.popleft()
            if current not in visited:
                visited.add(current)
                queue.extend(self._incoming.get(current, []))
        return visited

    def topological_sort(self) -> List[str]:
        in_degree = {nid: 0 for nid in self.nodes}
        for edge in self.edges:
            if edge.target in in_degree:
                in_degree[edge.target] = in_degree.get(edge.target, 0) + 1
        queue = deque([nid for nid in self.nodes if in_degree.get(nid, 0) == 0])
        result: List[str] = []
        while queue:
            current = queue.popleft()
            result.append(current)
            for neighbor in self._outgoing.get(current, []):
                in_degree[neighbor] = in_degree.get(neighbor, 0) - 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return result

    def is_acyclic(self) -> bool:
        return len(self.topological_sort()) == len(self.nodes)

    def find_paths(self, start: str, end: str, max_paths: int = 10) -> List[List[str]]:
        if start not in self.nodes or end not in self.nodes:
            return []
        paths: List[List[str]] = []
        stack = [(start, [start])]
        while stack and len(paths) < max_paths:
            current, path = stack.pop()
            if current == end:
                paths.append(path)
                continue
            for neighbor in self._outgoing.get(current, []):
                if neighbor not in path:
                    stack.append((neighbor, path + [neighbor]))
        return paths

    def find_shortest_path(self, start: str, end: str) -> Optional[List[str]]:
        if start not in self.nodes or end not in self.nodes:
            return None
        queue = deque([(start, [start])])
        visited = {start}
        while queue:
            current, path = queue.popleft()
            if current == end:
                return path
            for neighbor in self._outgoing.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def edge(self, source: str, target: str) -> Optional[CausalEdge]:
        for e in self.edges:
            if e.source == source and e.target == target:
                return e
        return None
