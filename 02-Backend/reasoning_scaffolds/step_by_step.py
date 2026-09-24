from __future__ import annotations

from typing import Callable, List, Optional


class StepByStepResult:
    def __init__(self, steps: List[str], final: str) -> None:
        self.steps = steps
        self.final = final

    def __repr__(self) -> str:
        return f"StepByStepResult(steps={self.steps!r}, final={self.final!r})"


def step_by_step(
    problem: str,
    step_fn: Callable[[str, List[str]], str],
    max_steps: int = 10,
    stop_condition: Optional[Callable[[str, List[str]], bool]] = None,
) -> StepByStepResult:
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    if not problem.strip():
        raise ValueError("problem must not be empty")
    if step_fn is None:
        raise ValueError("step_fn must be provided")

    steps: List[str] = []
    current = problem

    for _ in range(max_steps):
        next_step = step_fn(current, steps)
        if not isinstance(next_step, str):
            raise TypeError("step_fn must return a string")
        next_step = next_step.strip()
        if not next_step:
            break
        steps.append(next_step)
        if stop_condition is not None and stop_condition(next_step, steps):
            break
        current = next_step

    final = steps[-1] if steps else ""
    return StepByStepResult(steps=steps, final=final)
