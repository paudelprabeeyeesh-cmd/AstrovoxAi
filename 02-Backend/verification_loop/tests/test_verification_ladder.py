import numpy as np
from verification_loop.verification_ladder import LadderStage, StageResult, VerificationLadder


def _checker(passed: bool = True, error_count: int = 0):
    def _inner():
        return {"passed": passed, "error_count": error_count}
    return _inner


def test_ladder_runs_all_stages_when_passing():
    ladder = VerificationLadder(stop_on_failure=False)
    checks = {stage: _checker() for stage in LadderStage}
    report = ladder.run(checks)
    assert report["stages_run"] == len(LadderStage)
    assert report["stages_passed"] == len(LadderStage)
    assert report["stages_failed"] == 0


def test_ladder_stops_on_first_failure():
    ladder = VerificationLadder(stop_on_failure=True)
    failing = _checker(passed=False, error_count=2)
    checks = {LadderStage.SYNTAX: failing}
    report = ladder.run(checks)
    assert report["stages_run"] == 1
    assert report["stages_failed"] == 1


def test_ladder_continues_when_disabled():
    ladder = VerificationLadder(stop_on_failure=False)
    failing = _checker(passed=False, error_count=1)
    checks = {stage: failing for stage in LadderStage}
    report = ladder.run(checks)
    assert report["stages_run"] == len(LadderStage)
    assert report["stages_failed"] == len(LadderStage)


def test_ladder_duration_metrics_are_numeric():
    ladder = VerificationLadder(stop_on_failure=False)
    checks = {LadderStage.BUILD: _checker()}
    report = ladder.run(checks)
    assert isinstance(report["total_duration_ms"], float)
    assert report["mean_duration_ms"] >= 0.0
    assert 0.0 <= report["p95_duration_ms"] <= report["total_duration_ms"]


def test_stage_result_defaults():
    result = StageResult(stage=LadderStage.LINT, passed=True, duration_ms=1.0, error_count=0)
    assert result.details == {}


def test_ladder_result_serialization():
    ladder = VerificationLadder(stop_on_failure=False)
    checks = {LadderStage.FULL_SUITE: _checker()}
    report = ladder.run(checks)
    stage_dict = report["results"][0]
    assert "stage" in stage_dict
    assert "passed" in stage_dict
    assert "duration_ms" in stage_dict
