import numpy as np
import pytest

from metacognition.metacognitive_monitor import MetacognitiveMonitor, ConfidenceState


def test_init_defaults():
    monitor = MetacognitiveMonitor()
    assert monitor.decay_rate == 0.95
    assert monitor.history == []
    assert monitor.task_difficulty == {}


def test_track_first_observation():
    monitor = MetacognitiveMonitor()
    state = monitor.track("task1", performance=0.8, expected_difficulty=0.5)
    assert isinstance(state, ConfidenceState)
    assert 0.0 <= state.overall <= 1.0
    assert 0.0 <= state.uncertainty <= 1.0
    assert state.overall == pytest.approx(min(1.0, 0.8 / 0.5))
    assert state.uncertainty == pytest.approx(1.0 - state.overall)
    assert len(monitor.history) == 1
    assert "task1" in monitor.task_difficulty


def test_track_second_observation_decays_difficulty():
    monitor = MetacognitiveMonitor(decay_rate=0.9)
    monitor.track("task1", performance=0.8, expected_difficulty=0.5)
    state = monitor.track("task1", performance=0.8, expected_difficulty=0.5)
    expected_difficulty = 0.5 * 0.9 + 0.5 * (1 - 0.9)
    assert monitor.task_difficulty["task1"] == pytest.approx(expected_difficulty)
    assert state.overall == pytest.approx(min(1.0, 0.8 / expected_difficulty))


def test_track_confidence_bounded():
    monitor = MetacognitiveMonitor()
    state = monitor.track("task1", performance=2.0, expected_difficulty=0.1)
    assert 0.0 <= state.overall <= 1.0
    assert 0.0 <= state.uncertainty <= 1.0


def test_estimate_uncertainty_first_call():
    monitor = MetacognitiveMonitor()
    uncertainty = monitor.estimate_uncertainty("task1", evidence_count=0, coherence=0.8)
    assert 0.0 <= uncertainty <= 1.0
    assert monitor.task_difficulty["task1"] == 0.5


def test_estimate_uncertainty_decreases_with_evidence():
    monitor = MetacognitiveMonitor()
    monitor.task_difficulty["task1"] = 0.5
    low = monitor.estimate_uncertainty("task1", evidence_count=10, coherence=0.8)
    high = monitor.estimate_uncertainty("task1", evidence_count=0, coherence=0.8)
    assert low < high


def test_estimate_uncertainty_increases_with_difficulty():
    monitor = MetacognitiveMonitor()
    monitor.task_difficulty["task1"] = 0.9
    high = monitor.estimate_uncertainty("task1", evidence_count=0, coherence=0.8)
    monitor.task_difficulty["task1"] = 0.1
    low = monitor.estimate_uncertainty("task1", evidence_count=0, coherence=0.8)
    assert high > low


def test_estimate_uncertainty_bounded():
    monitor = MetacognitiveMonitor()
    u = monitor.estimate_uncertainty("task1", evidence_count=0, coherence=0.0)
    assert 0.0 <= u <= 1.0


def test_know_what_you_know_high_confidence():
    monitor = MetacognitiveMonitor()
    result = monitor.know_what_you_know("task1", performance=0.9, evidence_count=10)
    assert "confidence" in result
    assert "uncertainty" in result
    assert "knows_boundary" in result
    assert result["knows_boundary"] is True


def test_know_what_you_know_low_confidence():
    monitor = MetacognitiveMonitor()
    result = monitor.know_what_you_know("task1", performance=0.1, evidence_count=1)
    assert result["knows_boundary"] == False


def test_know_what_you_know_bounded():
    monitor = MetacognitiveMonitor()
    result = monitor.know_what_you_know("task1", performance=1.0, evidence_count=100)
    assert 0.0 <= result["confidence"] <= 1.0
    assert 0.0 <= result["uncertainty"] <= 1.0


def test_detect_unknowns_high_uncertainty():
    monitor = MetacognitiveMonitor()
    monitor.task_difficulty["task1"] = 0.9
    unknowns = monitor.detect_unknowns("task1", performance=0.9, coherence=0.0)
    assert "High uncertainty detected" in unknowns


def test_detect_unknowns_low_coherence():
    monitor = MetacognitiveMonitor()
    unknowns = monitor.detect_unknowns("task1", performance=0.9, coherence=0.1)
    assert "Low coherence in reasoning" in unknowns


def test_detect_unknowns_poor_performance():
    monitor = MetacognitiveMonitor()
    unknowns = monitor.detect_unknowns("task1", performance=0.1, coherence=1.0)
    assert "Poor performance on task" in unknowns


def test_detect_unknowns_no_issues():
    monitor = MetacognitiveMonitor()
    unknowns = monitor.detect_unknowns("task1", performance=0.9, coherence=0.9)
    assert unknowns == []


def test_get_calibration_report_empty():
    monitor = MetacognitiveMonitor()
    report = monitor.get_calibration_report()
    assert report["mean_calibration_error"] == 0.0
    assert report["overconfidence_rate"] == 0.0


def test_get_calibration_report():
    monitor = MetacognitiveMonitor()
    monitor.track("task1", performance=0.8, expected_difficulty=0.5)
    monitor.track("task1", performance=0.2, expected_difficulty=0.5)
    report = monitor.get_calibration_report()
    assert "mean_calibration_error" in report
    assert "overconfidence_rate" in report
    assert 0.0 <= report["mean_calibration_error"] <= 1.0
    assert 0.0 <= report["overconfidence_rate"] <= 1.0


def test_update_belief_default_prior():
    monitor = MetacognitiveMonitor()
    updated = monitor.update_belief("belief1", evidence=0.8)
    assert updated == pytest.approx(0.5 * 0.7 + 0.8 * 0.3)
    assert monitor.task_difficulty["belief1"] == pytest.approx(updated)


def test_update_belief_custom_prior():
    monitor = MetacognitiveMonitor()
    updated = monitor.update_belief("belief1", evidence=0.8, prior=0.2)
    assert updated == pytest.approx(0.2 * 0.7 + 0.8 * 0.3)


def test_calibration_error_zero_for_perfect_match():
    monitor = MetacognitiveMonitor()
    monitor.track("task1", performance=0.8, expected_difficulty=0.5)
    state = monitor.history[-1]
    assert state.calibration_error == pytest.approx(abs(state.overall - 0.8))


def test_history_appended():
    monitor = MetacognitiveMonitor()
    monitor.track("task1", 0.8, 0.5)
    monitor.track("task1", 0.5, 0.5)
    assert len(monitor.history) == 2


def test_different_tasks_tracked_independently():
    monitor = MetacognitiveMonitor()
    monitor.track("task1", 0.8, 0.5)
    monitor.track("task2", 0.3, 0.9)
    assert "task1" in monitor.task_difficulty
    assert "task2" in monitor.task_difficulty
    assert monitor.task_difficulty["task1"] != monitor.task_difficulty["task2"]


def test_track_returns_confidence_state_fields():
    monitor = MetacognitiveMonitor()
    state = monitor.track("task1", performance=0.6, expected_difficulty=0.5)
    assert hasattr(state, "overall")
    assert hasattr(state, "dimensions")
    assert hasattr(state, "uncertainty")
    assert hasattr(state, "calibration_error")


def test_estimate_uncertainty_bounded_extremes():
    monitor = MetacognitiveMonitor()
    monitor.task_difficulty["task1"] = 1.0
    u = monitor.estimate_uncertainty("task1", evidence_count=0, coherence=0.0)
    assert 0.0 <= u <= 1.0
