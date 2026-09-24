from __future__ import annotations

import pytest

from reasoning_scaffolds.chain_of_thought import chain_of_thought, _build_prompt


def fake_generate_step(prompt: str, steps: list[str]) -> str:
    return f"step-{len(steps) + 1}"


def fake_final_answer(problem: str, steps: list[str]) -> str:
    return f"answer({len(steps)})"


def test_chain_of_thought_generates_steps():
    answer = chain_of_thought("Solve x", fake_generate_step, num_steps=3)
    assert answer == "step-3"


def test_chain_of_thought_with_final_answer():
    answer = chain_of_thought("Solve x", fake_generate_step, num_steps=4, final_answer_fn=fake_final_answer)
    assert answer == "answer(4)"


def test_chain_of_thought_empty_on_no_steps():
    def no_steps(prompt: str, steps: list[str]) -> str:
        return ""
    answer = chain_of_thought("Solve x", no_steps, num_steps=3)
    assert answer == ""


def test_build_prompt_empty_steps():
    prompt = _build_prompt("Problem?", [])
    assert "step by step" in prompt.lower()


def test_build_prompt_with_steps():
    prompt = _build_prompt("Problem?", ["step1", "step2"])
    assert "Step 1: step1" in prompt
    assert "Step 2: step2" in prompt
