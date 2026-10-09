from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class ModuleNode:
    name: str
    file_path: str
    imports: List[str] = field(default_factory=list)


class DependencyMapper:
    def __init__(self) -> None:
        self._modules: Dict[str, ModuleNode] = {}
        self._file_to_module: Dict[str, str] = {}
        self._adj: Dict[str, Set[str]] = {}

    def add_module(self, name: str, file_path: str, imports: List[str]) -> None:
        self._modules[name] = ModuleNode(name=name, file_path=file_path, imports=imports)
        self._file_to_module[file_path] = name
        self._adj.setdefault(name, set())
        for imp in imports:
            self._adj.setdefault(imp, set())
            self._adj[name].add(imp)

    def detect_cycles(self) -> List[List[str]]:
        cycles: List[List[str]] = []
        visited = set()
        rec_stack = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in sorted(self._adj.get(node, [])):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    start = path.index(neighbor)
                    cycles.append(path[start:])
            path.pop()
            rec_stack.discard(node)

        for node in sorted(self._modules.keys()):
            if node not in visited:
                dfs(node)
        return cycles

    def topo_sort(self) -> Optional[List[str]]:
        out_degree = {name: len(self._adj.get(name, set())) for name in self._modules}
        reverse_adj: Dict[str, Set[str]] = {name: set() for name in self._modules}
        for src, dests in self._adj.items():
            for dest in dests:
                if dest in reverse_adj:
                    reverse_adj[dest].add(src)

        queue = [name for name, deg in out_degree.items() if deg == 0]
        order: List[str] = []
        while queue:
            queue.sort()
            node = queue.pop(0)
            order.append(node)
            for neighbor in reverse_adj.get(node, []):
                out_degree[neighbor] -= 1
                if out_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) == len(self._modules):
            return order
        return None
