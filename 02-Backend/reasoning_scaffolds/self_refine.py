from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class RefineStep:
    iteration: int
    content: str
    critique: str
    revised: str


def self_refine(
    problem: str,
    generate_fn: Callable[[str], str],
    critique_fn: Callable[[str, str], str],
    revise_fn: Callable[[str, str], str],
    max_iterations: int = 3,
    initial_draft: Optional[str] = None,
) -> RefineStep:
    current = initial_draft or generate_fn(problem)
    history: List[RefineStep] = []

    for i in range(max_iterations):
        critique = critique_fn(problem, current)
        revised = revise_fn(problem, current, critique)
        step = RefineStep(iteration=i, content=current, critique=critique, revised=revised)
        history.append(step)
        if revised.strip() == current.strip():
            break
        current = revised

    return history[-1]
