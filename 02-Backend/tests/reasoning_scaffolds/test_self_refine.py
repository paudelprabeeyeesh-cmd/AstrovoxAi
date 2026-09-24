from __future__ import annotations

import pytest

from reasoning_scaffolds.self_refine import self_refine, RefineStep


def test_self_refine_single_iteration():
    calls = []

    def gen(problem: str) -> str:
        return "draft"

    def critique(problem: str, draft: str) -> str:
        calls.append("critique")
        return "needs work"

    def revise(problem: str, draft: str, feedback: str) -> str:
        calls.append("revise")
        return "revised"

    step = self_refine("p", gen, critique, revise, max_iterations=1)
    assert step.revised == "revised"
    assert "critique" in calls


def test_self_refine_stops_when_stable():
    def gen(problem: str) -> str:
        return "same"

    def critique(problem: str, draft: str) -> str:
        return "same"

    def revise(problem: str, draft: str, feedback: str) -> str:
        return draft

    step = self_refine("p", gen, critique, revise, max_iterations=3)
    assert step.content == "same"
    assert step.revised == "same"


def test_refine_step_fields():
    step = RefineStep(iteration=0, content="c", critique="cr", revised="r")
    assert step.iteration == 0
    assert step.content == "c"
