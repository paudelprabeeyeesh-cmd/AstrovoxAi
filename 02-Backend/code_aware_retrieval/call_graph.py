import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np


@dataclass
class FunctionDef:
    fqn: str
    file_path: str
    line: int
    is_method: bool
    class_name: Optional[str]


@dataclass
class CallEdge:
    caller_fqn: str
    callee_name: str
    file_path: str
    line: int


class CallGraph:
    def __init__(self) -> None:
        self._funcs: Dict[str, FunctionDef] = {}
        self._calls: List[CallEdge] = []
        self._methods: Dict[str, Set[str]] = {}

    def register_function(self, fqn: str, file_path: str, line: int) -> None:
        parts = fqn.rsplit(".", 1)
        is_method = len(parts) == 2
        class_name = parts[0] if is_method else None
        self._funcs[fqn] = FunctionDef(
            fqn=fqn,
            file_path=file_path,
            line=line,
            is_method=is_method,
            class_name=class_name,
        )
        if class_name:
            self._methods.setdefault(class_name, set()).add(fqn)

    def add_call(
        self, caller_fqn: str, callee_name: str, file_path: str, line: int
    ) -> None:
        self._calls.append(
            CallEdge(
                caller_fqn=caller_fqn,
                callee_name=callee_name,
                file_path=file_path,
                line=line,
            )
        )

    def resolve_dynamic(self, callee_name: str, class_name: Optional[str]) -> List[str]:
        candidates: List[str] = []
        if class_name and class_name in self._methods:
            candidates.extend(
                f for f in self._methods[class_name] if f.endswith(f".{callee_name}")
            )
        if not candidates:
            for fqn, fdef in self._funcs.items():
                if fqn.endswith(f".{callee_name}") or fqn == callee_name:
                    candidates.append(fqn)
        return candidates

    def build_matrix(self) -> Tuple[np.ndarray, List[str]]:
        funcs = sorted(self._funcs.keys())
        idx = {f: i for i, f in enumerate(funcs)}
        n = len(funcs)
        mat = np.zeros((n, n), dtype=np.int32)
        for call in self._calls:
            resolved = self.resolve_dynamic(
                call.callee_name, self._funcs.get(call.caller_fqn).class_name
                if call.caller_fqn in self._funcs
                else None
            )
            ci = idx.get(call.caller_fqn)
            if ci is None:
                continue
            for callee in resolved:
                di = idx.get(callee)
                if di is not None:
                    mat[ci, di] += 1
        return mat, funcs

    def callers_of(self, fqn: str) -> List[str]:
        mat, funcs = self.build_matrix()
        if fqn not in funcs:
            return []
        di = funcs.index(fqn)
        return [funcs[i] for i in range(len(funcs)) if mat[i, di] > 0]

    def callees_of(self, fqn: str) -> List[str]:
        mat, funcs = self.build_matrix()
        if fqn not in funcs:
            return []
        ci = funcs.index(fqn)
        return [funcs[i] for i in range(len(funcs)) if mat[ci, i] > 0]
