from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np


@dataclass
class ModuleNode:
    name: str
    file_path: str
    imports: List[str] = field(default_factory=list)


class DependencyGraph:
    def __init__(self) -> None:
        self._modules: Dict[str, ModuleNode] = {}
        self._file_to_module: Dict[str, str] = {}

    def add_module(self, name: str, file_path: str, imports: List[str]) -> None:
        self._modules[name] = ModuleNode(name=name, file_path=file_path, imports=imports)
        self._file_to_module[file_path] = name

    def detect_cycles(self) -> List[List[str]]:
        modules = sorted(self._modules.keys())
        idx = {m: i for i, m in enumerate(modules)}
        n = len(modules)
        adj = np.zeros((n, n), dtype=np.int32)
        for mod in modules:
            mi = idx[mod]
            for imp in self._modules[mod].imports:
                if imp in idx:
                    adj[mi, idx[imp]] = 1
        cycles: List[List[str]] = []
        visited = [False] * n
        rec_stack = [False] * n
        path: List[str] = []

        def dfs(u: int) -> None:
            visited[u] = True
            rec_stack[u] = True
            path.append(modules[u])
            for v in range(n):
                if adj[u, v] == 0:
                    continue
                if not visited[v]:
                    dfs(v)
                elif rec_stack[v]:
                    cycle_start = path.index(modules[v])
                    cycles.append(path[cycle_start:])
            path.pop()
            rec_stack[u] = False

        for i in range(n):
            if not visited[i]:
                dfs(i)
        return cycles

    def topo_sort(self) -> List[str]:
        modules = sorted(self._modules.keys())
        idx = {m: i for i, m in enumerate(modules)}
        n = len(modules)
        adj = np.zeros((n, n), dtype=np.int32)
        for mod in modules:
            mi = idx[mod]
            for imp in self._modules[mod].imports:
                if imp in idx:
                    adj[mi, idx[imp]] = 1
        out_deg = np.zeros(n, dtype=np.int32)
        for i in range(n):
            for j in range(n):
                if adj[i, j] == 1:
                    out_deg[i] += 1
        queue = [i for i in range(n) if out_deg[i] == 0]
        order: List[str] = []
        while queue:
            u = queue.pop(0)
            order.append(modules[u])
            for v in range(n):
                if adj[v, u] == 1:
                    out_deg[v] -= 1
                    if out_deg[v] == 0:
                        queue.append(v)
        return order

    def module_of(self, file_path: str) -> Optional[str]:
        return self._file_to_module.get(file_path)

    def dependents_of(self, name: str) -> List[str]:
        modules = sorted(self._modules.keys())
        idx = {m: i for i, m in enumerate(modules)}
        n = len(modules)
        adj = np.zeros((n, n), dtype=np.int32)
        for mod in modules:
            mi = idx[mod]
            for imp in self._modules[mod].imports:
                if imp in idx:
                    adj[mi, idx[imp]] = 1
        if name not in idx:
            return []
        mi = idx[name]
        return [modules[i] for i in range(n) if adj[i, mi] == 1]
