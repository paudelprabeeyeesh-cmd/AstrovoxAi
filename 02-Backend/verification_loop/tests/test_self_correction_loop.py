import numpy as np
from verification_loop.self_correction_loop import (
    CorrectionConfig,
    CorrectionResult,
    SelfCorrectionLoop,
)


def test_self_correction_succeeds_on_first_attempt():
    loop = SelfCorrectionLoop(CorrectionConfig(max_attempts=3))
    result = loop.run(
        error="syntax error",
        model_fn=lambda e: "fixed",
        validator_fn=lambda out: {"passed": out == "fixed"},
    )
    assert result["converged"]
    assert result["attempts"] == 1
    assert result["final_error"] is None


def test_self_correction_retries_until_success():
    loop = SelfCorrectionLoop(CorrectionConfig(max_attempts=3))
    attempts = []
    def model_fn(e):
        attempts.append(1)
        return "attempt_" + str(len(attempts))
    def validator(out):
        return {"passed": out == "attempt_3"}
    result = loop.run("error", model_fn, validator)
    assert result["converged"]
    assert result["attempts"] == 3
    assert result["success_rate"] == round(1 / 3, 3)


def test_self_correction_exhausts_attempts():
    loop = SelfCorrectionLoop(CorrectionConfig(max_attempts=2))
    result = loop.run(
        error="bad",
        model_fn=lambda e: "nope",
        validator_fn=lambda out: {"passed": False, "error": "still bad"},
    )
    assert not result["converged"]
    assert result["attempts"] == 2
    assert result["final_error"] is not None


def test_self_correction_duration_metrics():
    loop = SelfCorrectionLoop(CorrectionConfig(max_attempts=2))
    result = loop.run(
        error="e",
        model_fn=lambda e: "x",
        validator_fn=lambda out: {"passed": True},
    )
    assert result["total_duration_ms"] >= 0.0
    assert result["mean_duration_ms"] >= 0.0
    assert len(result["history"]) == 1


def test_self_correction_history_records_attempts():
    loop = SelfCorrectionLoop(CorrectionConfig(max_attempts=3))
    result = loop.run(
        error="e",
        model_fn=lambda e: "x",
        validator_fn=lambda out: {"passed": True},
    )
    assert result["history"][0]["attempt"] == 1
    assert result["history"][0]["success"] is True
    assert "duration_ms" in result["history"][0]
