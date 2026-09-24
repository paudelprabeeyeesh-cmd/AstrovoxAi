from __future__ import annotations

import pytest

from reasoning_scaffolds.step_by_step import StepByStepResult, step_by_step


def fake_step(current: str, steps: list[str]) -> str:
    return f"step-{len(steps) + 1}"


def test_step_by_step_generates_steps():
    result = step_by_step("Solve x", fake_step, max_steps=3)
    assert isinstance(result, StepByStepResult)
    assert result.steps == ["step-1", "step-2", "step-3"]
    assert result.final == "step-3"


def test_step_by_step_stops_on_empty_step():
    def stop_early(current: str, steps: list[str]) -> str:
        if len(steps) >= 2:
            return ""
        return f"step-{len(steps) + 1}"

    result = step_by_step("Solve x", stop_early, max_steps=5)
    assert result.steps == ["step-1", "step-2"]
    assert result.final == "step-2"


def test_step_by_step_stop_condition():
    def step_fn(current: str, steps: list[str]) -> str:
        return f"step-{len(steps) + 1}"

    def stop_when_three(current: str, steps: list[str]) -> bool:
        return len(steps) == 3

    result = step_by_step("Solve x", step_fn, max_steps=10, stop_condition=stop_when_three)
    assert len(result.steps) == 3
    assert result.final == "step-3"


def test_step_by_step_empty_problem_raises():
    with pytest.raises(ValueError):
        step_by_step("", fake_step, max_steps=3)


def test_step_by_step_zero_max_steps_raises():
    with pytest.raises(ValueError):
        step_by_step("Solve x", fake_step, max_steps=0)


def test_step_by_step_none_step_fn_raises():
    with pytest.raises(ValueError):
        step_by_step("Solve x", None, max_steps=3)  # type: ignore[arg-type]


def test_step_by_step_non_string_return_raises():
    def bad_step(current: str, steps: list[str]) -> int:
        return 1

    with pytest.raises(TypeError):
        step_by_step("Solve x", bad_step, max_steps=3)
