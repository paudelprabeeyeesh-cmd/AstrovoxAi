import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from models.llm.healing.analyzer import AnalysisReport, LogEntry, Pattern, RootCause, RootCauseAnalyzer
from models.llm.healing.detector import FailureDetector, HealthCheck, HealthResult, HealthStatus
from models.llm.healing.notifier import Alert, EscalationPolicy, NotificationChannel, Notifier
from models.llm.healing.recovery import Checkpoint, Recovery, RecoveryResult, RecoveryStatus


@pytest.fixture
def logs() -> Sequence[LogEntry]:
    return [
        {
            "timestamp": "2026-09-28T17:00:00Z",
            "level": "ERROR",
            "source": "training",
            "message": "CUDA out of memory (code: OOM)",
            "metadata": {"run_id": "run-1"},
        },
        {
            "timestamp": "2026-09-28T17:00:01Z",
            "level": "WARNING",
            "source": "training",
            "message": "Learning rate dropped below threshold",
            "metadata": {},
        },
        {
            "timestamp": "2026-09-28T17:00:02Z",
            "level": "ERROR",
            "source": "training",
            "message": "NaN loss detected (code: NAN_LOSS)",
            "metadata": {"step": 100},
        },
        {
            "timestamp": "2026-09-28T17:00:03Z",
            "level": "INFO",
            "source": "training",
            "message": "checkpoint saved",
            "metadata": {},
        },
    ]


@pytest.fixture
def oom_pattern() -> Pattern:
    return Pattern(
        name="OOM",
        regex=r"CUDA out of memory \(code: (?P<code>[^)]+)\)",
    )


@pytest.fixture
def nan_pattern() -> Pattern:
    return Pattern(
        name="NAN_LOSS",
        regex=r"NaN loss detected \(code: (?P<code>[^)]+)\)",
    )


@pytest.fixture
def analyzer(oom_pattern: Pattern, nan_pattern: Pattern) -> RootCauseAnalyzer:
    return RootCauseAnalyzer(patterns=[oom_pattern, nan_pattern])


@pytest.fixture
def notifier() -> Notifier:
    return Notifier(
        policies=[
            EscalationPolicy(
                name="critical",
                rules=[{"severities": ["critical", "error"], "channel": "email"}],
            )
        ]
    )


class TestHealthDetector:
    def test_health_result_creation(self) -> None:
        result = HealthResult(
            checks=[],
            overall_status=HealthStatus.PASS,
            summary="ok",
            checked_at="2026-09-28T17:00:00Z",
        )
        assert result.overall_status == HealthStatus.PASS
        assert result.summary == "ok"

    def test_check_returns_all_checks(self) -> None:
        detector = FailureDetector(checkers=[lambda: {"name": "cuda", "status": HealthStatus.PASS, "checked_at": "2026-09-28T17:00:00Z"}])
        result = detector.check()
        assert len(result.checks) == 1
        assert result.overall_status == HealthStatus.PASS

    def test_check_marks_failure(self) -> None:
        detector = FailureDetector(checkers=[lambda: {"name": "cuda", "status": HealthStatus.FAIL, "message": "missing", "checked_at": "2026-09-28T17:00:00Z"}])
        result = detector.check()
        assert result.overall_status == HealthStatus.FAIL
        assert len(result.failures) == 1

    def test_check_marks_warning(self) -> None:
        detector = FailureDetector(checkers=[lambda: {"name": "cuda", "status": HealthStatus.WARN, "checked_at": "2026-09-28T17:00:00Z"}])
        result = detector.check()
        assert result.overall_status == HealthStatus.WARN

    def test_anomaly_detection(self) -> None:
        detector = FailureDetector(checkers=[], anomaly_window=20, anomaly_threshold=2.5)
        for _ in range(10):
            detector.detect_anomalies(10.0)
        z = detector.detect_anomalies(50.0)
        assert z > 2.5

    def test_generate_alert(self) -> None:
        detector = FailureDetector(checkers=[lambda: {"name": "cuda", "status": HealthStatus.FAIL, "message": "missing", "checked_at": "2026-09-28T17:00:00Z"}])
        result = detector.check()
        alert = detector.generate_alert(result, channels=["log"])
        assert alert["severity"] == "critical"
        assert alert["status"] == "fail"

    def test_register(self) -> None:
        detector = FailureDetector(checkers=[])
        detector.register(lambda: {"name": "x", "status": HealthStatus.PASS, "checked_at": "2026-09-28T17:00:00Z"})
        result = detector.check()
        assert len(result.checks) == 1


class TestRootCauseAnalyzer:
    def test_analyze_empty(self, analyzer: RootCauseAnalyzer) -> None:
        report = analyzer.analyze([])
        assert report.root_causes == []
        assert report.summary == "0 logs analyzed"

    def test_analyze_matches_patterns(self, analyzer: RootCauseAnalyzer, logs: Sequence[LogEntry]) -> None:
        report = analyzer.analyze(logs)
        assert report.error_count == 2
        assert len(report.root_causes) == 2
        codes = [rc.code for rc in report.root_causes]
        assert "OOM" in codes
        assert "NAN_LOSS" in codes

    def test_recommendations(self, analyzer: RootCauseAnalyzer, logs: Sequence[LogEntry]) -> None:
        report = analyzer.analyze(logs)
        assert len(report.recommendations) == 2
        actions = [rec.action for rec in report.recommendations]
        assert "reduce_batch_size" in actions or any("reduce" in a for a in actions)

    def test_log_count(self, analyzer: RootCauseAnalyzer, logs: Sequence[LogEntry]) -> None:
        report = analyzer.analyze(logs)
        assert report.log_count == len(logs)

    def test_add_pattern(self, analyzer: RootCauseAnalyzer) -> None:
        analyzer.add_pattern(Pattern(name="NEW", regex=r"new issue \(code: (?P<code>[^)]+)\)"))
        assert len(analyzer.patterns) == 3

    def test_to_dict(self, analyzer: RootCauseAnalyzer, logs: Sequence[LogEntry]) -> None:
        report = analyzer.analyze(logs)
        data = report.to_dict()
        assert data["analyzed_at"]
        assert data["error_count"] == 2


class TestNotificationSystem:
    def test_route(self, notifier: Notifier) -> None:
        alert = Alert(alert_id="a1", severity="error", summary="x", status="fail", checked_at="2026-09-28T17:00:00Z")
        routes = notifier.route(alert)
        assert len(routes) == 1
        assert routes[0]["channel"] == "email"

    def test_route_fallback(self) -> None:
        notifier = Notifier(policies=[])
        alert = Alert(alert_id="a1", severity="error", summary="x", status="fail", checked_at="2026-09-28T17:00:00Z")
        routes = notifier.route(alert)
        assert routes[0]["channel"] == "email"

    def test_send(self, notifier: Notifier) -> None:
        alert = Alert(alert_id="a1", severity="error", summary="x", status="fail", checked_at="2026-09-28T17:00:00Z")
        results = notifier.send(alert)
        assert len(results) == 1
        assert results[0]["status"] == "sent"

    def test_update_status(self, notifier: Notifier) -> None:
        alert = Alert(alert_id="a1", severity="error", summary="x", status="fail", checked_at="2026-09-28T17:00:00Z")
        update = notifier.update_status(alert, "resolved")
        assert update["status"] == "resolved"
        assert len(notifier.get_status_updates()) == 1

    def test_add_policy(self, notifier: Notifier) -> None:
        notifier.add_policy(EscalationPolicy(name="low", rules=[{"severities": ["warning"], "channel": "slack"}]))
        alert = Alert(alert_id="a1", severity="warning", summary="x", status="warn", checked_at="2026-09-28T17:00:00Z")
        routes = notifier.route(alert)
        assert any(r["channel"] == "slack" for r in routes)


class TestRecovery:
    def test_checkpoint_creation(self, tmp_path: Path) -> None:
        p = tmp_path / "ckpt.pt"
        p.write_text("model_state")
        checkpoint = Checkpoint(path=p, created_at="2026-09-28T17:00:00Z", metadata={})
        assert checkpoint.size_bytes > 0
        assert checkpoint.path.exists()

    def test_restore_checkpoint_success(self, tmp_path: Path) -> None:
        p = tmp_path / "ckpt.pt"
        p.write_text("state")
        checkpoint = Checkpoint(path=p, created_at="2026-09-28T17:00:00Z", metadata={})
        recovery = Recovery()
        assert recovery.restore_checkpoint(checkpoint) is True

    def test_restore_checkpoint_missing(self, tmp_path: Path) -> None:
        p = tmp_path / "missing.pt"
        checkpoint = Checkpoint(path=p, created_at="2026-09-28T17:00:00Z", metadata={})
        recovery = Recovery()
        assert recovery.restore_checkpoint(checkpoint) is False

    def test_cleanup_resources(self, tmp_path: Path) -> None:
        d = tmp_path / "tmp_artifact"
        d.mkdir()
        (d / "f.txt").write_text("x")
        recovery = Recovery()
        result = recovery.cleanup_resources([d])
        assert result.status == RecoveryStatus.SUCCESS
        assert not d.exists()

    def test_cleanup_failures(self) -> None:
        recovery = Recovery()
        result = recovery.cleanup_resources([Path("/nonexistent")])
        assert result.status == RecoveryStatus.FAILED
        assert len(result.output["failed"]) == 1

    def test_register_checkpoint(self, tmp_path: Path) -> None:
        p = tmp_path / "c.pt"
        p.write_text("state")
        recovery = Recovery()
        recovery.register_checkpoint(Checkpoint(path=p, created_at="2026-09-28T17:00:00Z", metadata={}))
        assert len(recovery._checkpoints) == 1

    def test_attempt_recovery_max_exceeded(self) -> None:
        recovery = Recovery(max_attempts=1)
        for _ in range(2):
            recovery.attempt_recovery(RecoveryResult(status=RecoveryStatus.FAILED, action="x", started_at="2026-09-28T17:00:00Z", finished_at="2026-09-28T17:00:00Z", output={}))

    def test_attempt_recovery_success(self, tmp_path: Path) -> None:
        p = tmp_path / "c.pt"
        p.write_text("state")
        ckpt = Checkpoint(path=p, created_at="2026-09-28T17:00:00Z", metadata={})
        recovery = Recovery()
        result = recovery.attempt_recovery(RecoveryResult(status=RecoveryStatus.FAILED, action="x", started_at="2026-09-28T17:00:00Z", finished_at="2026-09-28T17:00:00Z", output={}), checkpoint=ckpt)
        assert result.status == RecoveryStatus.SUCCESS

    def test_attempt_recovery_missing_checkpoint(self) -> None:
        recovery = Recovery()
        p = Path("/missing.pt")
        ckpt = Checkpoint(path=p, created_at="2026-09-28T17:00:00Z", metadata={})
        result = recovery.attempt_recovery(RecoveryResult(status=RecoveryStatus.FAILED, action="x", started_at="2026-09-28T17:00:00Z", finished_at="2026-09-28T17:00:00Z", output={}), checkpoint=ckpt)
        assert result.status == RecoveryStatus.FAILED
