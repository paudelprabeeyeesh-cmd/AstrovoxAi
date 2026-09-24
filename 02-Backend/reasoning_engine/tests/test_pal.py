import numpy as np
import pytest
from reasoning_engine.pal import SandboxExecutor, PAL


def test_sandbox_execute_simple():
    ex = SandboxExecutor()
    result = ex.execute("x = 5")
    assert result == {"x": 5}


def test_sandbox_execute_with_result():
    ex = SandboxExecutor()
    result = ex.execute("result = 2 + 2")
    assert result == 4


def test_sandbox_execute_with_inputs():
    ex = SandboxExecutor()
    result = ex.execute("result = a + b", inputs={"a": 3, "b": 7})
    assert result == 10


def test_sandbox_execute_error():
    ex = SandboxExecutor()
    result = ex.execute("raise ValueError('bad')")
    assert "error" in result


def test_pal_generate():
    pal = PAL(generate_code_fn=lambda p: f"result = {p}")
    code = pal.generate_code("2+2")
    assert "result = 2+2" in code


def test_pal_run():
    pal = PAL(generate_code_fn=lambda p: "result = 10 * 2")
    out = pal.run("dummy")
    assert out["result"] == 20


def test_pal_score_execution():
    pal = PAL(generate_code_fn=lambda p: "result = 5")
    score = pal.score_execution("dummy", expected=5)
    assert abs(score - 1.0) < 1e-6


def test_pal_score_execution_wrong():
    pal = PAL(generate_code_fn=lambda p: "result = 5")
    score = pal.score_execution("dummy", expected=3)
    assert score < 1.0


def test_pal_score_execution_error():
    pal = PAL(generate_code_fn=lambda p: "raise ValueError()")
    score = pal.score_execution("dummy", expected=5)
    assert score == 0.0


def test_execute_with_trace():
    ex = SandboxExecutor()
    trace = ex.execute_with_trace("result = 1 + 1")
    assert trace["result"] == 2
    assert trace["error"] is None
