import numpy as np
import pytest
from reasoning_engine.self_refine import SelfRefine


def test_self_refine_generate():
    pipeline = SelfRefine(
        generate_fn=lambda p: f"gen_{p}",
        critique_fn=lambda t: "missing detail",
        revise_fn=lambda t, f: t + " revised",
        max_iterations=2,
    )
    out = pipeline.generate("prompt")
    assert out == "gen_prompt"


def test_self_refine_critique():
    pipeline = SelfRefine(
        generate_fn=lambda p: p,
        critique_fn=lambda t: "improve",
        revise_fn=lambda t, f: t + f,
        max_iterations=1,
    )
    fb = pipeline.critique("text")
    assert fb == "improve"


def test_self_refine_revise():
    pipeline = SelfRefine(
        generate_fn=lambda p: p,
        critique_fn=lambda t: "f",
        revise_fn=lambda t, f: t + "+" + f,
        max_iterations=1,
    )
    out = pipeline.revise("base", "f")
    assert out == "base+f"


def test_self_refine_run_loop():
    history_calls = []

    def gen(p):
        history_calls.append(("gen", p))
        return "v1"

    def crit(t):
        history_calls.append(("crit", t))
        return "needs work"

    def rev(t, f):
        history_calls.append(("rev", t, f))
        return t + "+" + f

    pipeline = SelfRefine(generate_fn=gen, critique_fn=crit, revise_fn=rev, max_iterations=2, improvement_threshold=0.5)
    result = pipeline.run("task")
    assert "final" in result
    assert "history" in result
    assert result["final"].startswith("v1")


def test_self_refine_early_stop():
    iterations = []

    def gen(p):
        return "base"

    def crit(t):
        return "feedback"

    def rev(t, f):
        iterations.append(t)
        return t + "+improved"

    pipeline = SelfRefine(
        generate_fn=gen,
        critique_fn=crit,
        revise_fn=rev,
        max_iterations=10,
        improvement_threshold=100.0,
    )
    result = pipeline.run("task")
    assert len(iterations) == 1


def test_self_refine_scores():
    pipeline = SelfRefine(
        generate_fn=lambda p: "short",
        critique_fn=lambda t: "more detail needed",
        revise_fn=lambda t, f: t + " more detail here",
        max_iterations=3,
        improvement_threshold=0.0,
    )
    result = pipeline.run("task")
    assert len(result["history"]) > 0
