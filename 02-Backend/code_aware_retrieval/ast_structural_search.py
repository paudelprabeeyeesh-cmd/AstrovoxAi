from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np


@dataclass
class ASTPattern:
    kind: str
    text_substr: Optional[str] = None
    attr_constraints: Dict[str, Any] = None
    children_patterns: List["ASTPattern"] = None

    def __post_init__(self) -> None:
        if self.attr_constraints is None:
            self.attr_constraints = {}
        if self.children_patterns is None:
            self.children_patterns = []


def _node_matches(node: Any, pattern: ASTPattern) -> bool:
    if hasattr(node, "kind") and node.kind != pattern.kind:
        return False
    if pattern.text_substr and pattern.text_substr not in getattr(node, "text", ""):
        return False
    for attr, val in pattern.attr_constraints.items():
        if getattr(node, attr, None) != val:
            return False
    return True


def _search(node: Any, pattern: ASTPattern, out: List[Any]) -> None:
    if _node_matches(node, pattern):
        if not pattern.children_patterns:
            out.append(node)
        elif len(getattr(node, "children", [])) == len(pattern.children_patterns):
            all_match = True
            for child, cp in zip(node.children, pattern.children_patterns):
                if not _node_matches(child, cp):
                    all_match = False
                    break
            if all_match:
                out.append(node)
    for child in getattr(node, "children", []):
        _search(child, pattern, out)


class ASTStructuralSearch:
    def __init__(self) -> None:
        self._index: List[Any] = []

    def index(self, nodes: List[Any]) -> None:
        self._index.extend(nodes)

    def query(self, pattern: ASTPattern) -> List[Any]:
        results: List[Any] = []
        for node in self._index:
            _search(node, pattern, results)
        return results

    def query_with_score(self, pattern: ASTPattern) -> List[Tuple[Any, float]]:
        results = self.query(pattern)
        scored: List[Tuple[Any, float]] = []
        for node in results:
            score = float(pattern.text_substr in getattr(node, "text", ""))
            scored.append((node, score))
        return scored
