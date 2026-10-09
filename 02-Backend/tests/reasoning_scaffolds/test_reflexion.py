from __future__ import annotations

import pytest

from reasoning_scaffolds.reflexion import ReflectionMemory, reflexion, _overlap


def test_reflection_memory_add_and_retrieve():
    mem = ReflectionMemory()
    mem.add("p1", "a1", "ok", True)
    mem.add("p2", "a2", "fail", False)
    assert len(mem.history) == 2


def test_reflection_memory_relevant():
    mem = ReflectionMemory()
    mem.add("solve for x", "attempt1", "fail", False)
    mem.add("compute y", "attempt2", "ok", True)
    relevant = mem.relevant("solve for x")
    assert relevant[0][0] == "solve for x"


def test_reflexion_succeeds_on_second_try():
    mem = ReflectionMemory()
    state = {"attempts": 0}

    def generate(problem: str, context: list[str]) -> str:
        state["attempts"] += 1
        return f"attempt-{state['attempts']}"

    def evaluate(attempt: str) -> bool:
        return state["attempts"] >= 2

    def reflect(attempt: str, feedback: str) -> str:
        return f"reflection of {attempt}"

    result, success = reflexion("p", generate, evaluate, reflect, mem, max_iterations=3)
    assert success is True
    assert result == "attempt-2"


def test_overlap_identical():
    assert _overlap("hello world", "hello world") == pytest.approx(1.0)


def test_overlap_disjoint():
    assert _overlap("alpha", "beta") == 0.0
