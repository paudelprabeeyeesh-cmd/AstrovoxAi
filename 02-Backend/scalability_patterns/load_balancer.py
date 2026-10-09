import threading
from typing import Dict, List, Optional


class RoundRobinLoadBalancer:
    def __init__(self, nodes: Optional[List[str]] = None) -> None:
        self._nodes = nodes or []
        self._index = 0
        self._lock = threading.Lock()

    def add_node(self, node: str) -> None:
        with self._lock:
            self._nodes.append(node)

    def remove_node(self, node: str) -> None:
        with self._lock:
            self._nodes = [n for n in self._nodes if n != node]

    def select(self) -> Optional[str]:
        if not self._nodes:
            return None
        with self._lock:
            node = self._nodes[self._index % len(self._nodes)]
            self._index += 1
            return node

    def nodes(self) -> List[str]:
        return list(self._nodes)


class WeightedLoadBalancer:
    def __init__(self, weights: Optional[Dict[str, int]] = None) -> None:
        self._weights = weights or {}
        self._current: Dict[str, int] = {k: 0 for k in self._weights}
        self._lock = threading.Lock()

    def add_node(self, node: str, weight: int = 1) -> None:
        with self._lock:
            self._weights[node] = weight
            self._current[node] = 0

    def remove_node(self, node: str) -> None:
        with self._lock:
            self._weights.pop(node, None)
            self._current.pop(node, None)

    def select(self) -> Optional[str]:
        if not self._weights:
            return None
        with self._lock:
            for node in self._weights:
                self._current[node] = self._current.get(node, 0) + self._weights[node]
            best = max(self._weights, key=lambda node: self._current[node])
            self._current[best] -= sum(self._weights.values())
            return best

    def nodes(self) -> List[str]:
        return list(self._weights.keys())
