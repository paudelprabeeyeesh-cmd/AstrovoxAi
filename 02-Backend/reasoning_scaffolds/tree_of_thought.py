from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class ThoughtNode:
    thought: str
    score: float = 0.0
    children: List["ThoughtNode"] = field(default_factory=list)
    parent: Optional["ThoughtNode"] = field(default=None, repr=False)
    visits: int = 0
    value: float = 0.0
    is_terminal: bool = False
    metadata: dict = field(default_factory=dict)


def tot_search(
    problem: str,
    generate_fn: Callable[[str, List[str]], List[str]],
    evaluate_fn: Callable[[str, List[str]], float],
    depth: int = 3,
    branching_factor: int = 3,
    beam_width: int = 2,
) -> Optional[ThoughtNode]:
    root = ThoughtNode(thought=problem, score=evaluate_fn(problem, []))
    leaves: List[ThoughtNode] = [root]

    for _ in range(depth):
        candidates: List[ThoughtNode] = []
        for leaf in leaves:
            if leaf.is_terminal:
                candidates.append(leaf)
                continue
            thoughts = generate_fn(leaf.thought, [c.thought for c in _ancestors(leaf)])
            for t in thoughts[:branching_factor]:
                child = ThoughtNode(
                    thought=t,
                    score=evaluate_fn(t, [c.thought for c in _ancestors(leaf)] + [t]),
                    parent=leaf,
                )
                leaf.children.append(child)
                candidates.append(child)
        candidates.sort(key=lambda n: n.score, reverse=True)
        leaves = candidates[:beam_width]

    return max(leaves, key=lambda n: n.score) if leaves else root


def _ancestors(node: ThoughtNode) -> List[ThoughtNode]:
    path: List[ThoughtNode] = []
    current = node.parent
    while current is not None:
        path.append(current)
        current = current.parent
    return list(reversed(path))
