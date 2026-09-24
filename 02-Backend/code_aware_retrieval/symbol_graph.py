from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import numpy as np


@dataclass
class SymbolDef:
    fqn: str
    kind: str
    file_path: str
    line: int
    col: int


class SymbolGraph:
    def __init__(self) -> None:
        self._defs: Dict[str, SymbolDef] = {}
        self._refs: Dict[str, Set[str]] = {}
        self._files: List[str] = []
        self._file_idx: Dict[str, int] = {}
        self._adj: Optional[np.ndarray] = None

    def _ensure_adj(self) -> None:
        n = len(self._files)
        if self._adj is None or self._adj.shape[0] != n:
            self._adj = np.zeros((max(n, 1), max(n, 1)), dtype=np.int32)

    def index_file(self, file_path: str, symbols: List[SymbolDef]) -> None:
        for sym in symbols:
            if sym.file_path not in self._file_idx:
                self._file_idx[sym.file_path] = len(self._files)
                self._files.append(sym.file_path)
        if file_path not in self._file_idx:
            self._file_idx[file_path] = len(self._files)
            self._files.append(file_path)
        for sym in symbols:
            self._defs[sym.fqn] = sym
            self._refs.setdefault(sym.fqn, set())
        self._ensure_adj()

    def add_cross_ref(self, from_fqn: str, to_fqn: str) -> None:
        self._refs.setdefault(to_fqn, set()).add(from_fqn)

    def get_definition(self, fqn: str) -> Optional[SymbolDef]:
        return self._defs.get(fqn)

    def get_references(self, fqn: str) -> Set[str]:
        return self._refs.get(fqn, set())

    def build_adjacency(self) -> np.ndarray:
        self._ensure_adj()
        n = len(self._files)
        adj = np.zeros((n, n), dtype=np.int32)
        for fqn, refs in self._refs.items():
            defn = self._defs.get(fqn)
            if defn is None:
                continue
            fi = self._file_idx.get(defn.file_path)
            if fi is None:
                continue
            for ref_fqn in refs:
                ref_def = self._defs.get(ref_fqn)
                if ref_def is None:
                    continue
                ri = self._file_idx.get(ref_def.file_path)
                if ri is None:
                    continue
                adj[ri, fi] += 1
        self._adj = adj
        return adj

    def shortest_file_path(self, src: str, dst: str) -> Optional[List[str]]:
        self.build_adjacency()
        if self._adj is None or self._adj.shape[0] == 0:
            return None
        n = self._adj.shape[0]
        si = self._file_idx.get(src)
        di = self._file_idx.get(dst)
        if si is None or di is None:
            return None
        dist = np.full(n, -1, dtype=np.int32)
        prev = np.full(n, -1, dtype=np.int32)
        queue = [si]
        dist[si] = 0
        head = 0
        while head < len(queue):
            u = queue[head]
            head += 1
            if u == di:
                break
            for v in range(n):
                if self._adj[u, v] > 0 and dist[v] == -1:
                    dist[v] = dist[u] + 1
                    prev[v] = u
                    queue.append(v)
        if dist[di] == -1:
            return None
        path: List[str] = []
        cur = di
        while cur != -1:
            path.append(self._files[cur])
            cur = prev[cur]
        path.reverse()
        return path
