from __future__ import annotations

from typing import Callable, List, Optional


def chain_of_thought(
    problem: str,
    generate_step_fn: Callable[[str, List[str]], str],
    num_steps: int = 5,
    final_answer_fn: Optional[Callable[[str, List[str]], str]] = None,
) -> str:
    steps: List[str] = []
    prompt = problem
    for _ in range(num_steps):
        step = generate_step_fn(prompt, steps)
        if not step:
            break
        steps.append(step)
        prompt = _build_prompt(problem, steps)

    if final_answer_fn is not None:
        return final_answer_fn(problem, steps)
    return steps[-1] if steps else ""


def _build_prompt(problem: str, steps: List[str]) -> str:
    header = f"Problem: {problem}\n"
    if not steps:
        return header + "Let's reason step by step."
    body = "\n".join(f"Step {i + 1}: {s}" for i, s in enumerate(steps))
    return header + body + "\nNext step:"
