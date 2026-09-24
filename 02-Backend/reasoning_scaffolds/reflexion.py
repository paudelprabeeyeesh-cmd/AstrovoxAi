from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple


class ReflectionMemory:
    def __init__(self) -> None:
        self.history: List[Tuple[str, str, str, bool]] = []

    def add(self, problem: str, attempt: str, feedback: str, success: bool) -> None:
        self.history.append((problem, attempt, feedback, success))

    def relevant(self, problem: str, max_items: int = 5) -> List[Tuple[str, str, str, bool]]:
        scored = []
        for past_prob, past_attempt, past_feedback, past_success in self.history:
            similarity = _overlap(problem, past_prob)
            scored.append((similarity, past_prob, past_attempt, past_feedback, past_success))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(p, a, f, s) for _, p, a, f, s in scored[:max_items]]


def _overlap(a: str, b: str) -> float:
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / (len(set_a | set_b) + 1e-8)


def reflexion(
    problem: str,
    generate_fn: Callable[[str, List[str]], str],
    evaluate_fn: Callable[[str], bool],
    reflect_fn: Callable[[str, str], str],
    memory: ReflectionMemory,
    max_iterations: int = 3,
) -> Tuple[str, bool]:
    attempts: List[str] = []
    for i in range(max_iterations):
        context = _build_context(memory.relevant(problem))
        attempt = generate_fn(problem, context)
        attempts.append(attempt)
        success = evaluate_fn(attempt)
        feedback = "Success" if success else "Failure"
        memory.add(problem, attempt, feedback, success)
        if success:
            return attempt, True
        reflection = reflect_fn(attempt, feedback)
        attempts.append(reflection)
    return attempts[-1], False


def _build_context(history: List[Tuple[str, str, str, bool]]) -> List[str]:
    return [f"Problem: {p}\nAttempt: {a}\nOutcome: {f}" for p, a, f, _ in history]
