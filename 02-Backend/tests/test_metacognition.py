from metacognition.metacognitive_monitor import MetacognitiveMonitor


class TestMetacognitiveMonitor:
    def test_track_improves_with_performance(self):
        monitor = MetacognitiveMonitor()
        state = monitor.track("t1", performance=0.9, expected_difficulty=0.5)
        assert 0.0 <= state.overall <= 1.0
        assert state.overall > 0.0

    def test_estimate_uncertainty_high_with_no_evidence(self):
        monitor = MetacognitiveMonitor()
        monitor.task_difficulty["t1"] = 0.8
        unc = monitor.estimate_uncertainty("t1", evidence_count=0, coherence=0.3)
        assert 0.0 <= unc <= 1.0
        assert unc > 0.3

    def test_know_what_you_know(self):
        monitor = MetacognitiveMonitor()
        result = monitor.know_what_you_know("t1", performance=0.8, evidence_count=5)
        assert "confidence" in result
        assert "uncertainty" in result
        assert "knows_boundary" in result

    def test_detect_unknowns(self):
        monitor = MetacognitiveMonitor()
        monitor.task_difficulty["t1"] = 0.9
        unknowns = monitor.detect_unknowns("t1", performance=0.3, coherence=0.3)
        assert len(unknowns) > 0
        assert any("uncertainty" in u.lower() or "coherence" in u.lower() or "performance" in u.lower() for u in unknowns)

    def test_calibration_report(self):
        monitor = MetacognitiveMonitor()
        monitor.track("t1", performance=0.8, expected_difficulty=0.5)
        monitor.track("t2", performance=0.9, expected_difficulty=0.3)
        report = monitor.get_calibration_report()
        assert "mean_calibration_error" in report
        assert "overconfidence_rate" in report

    def test_update_belief(self):
        monitor = MetacognitiveMonitor()
        new_val = monitor.update_belief("b1", evidence=0.8, prior=0.5)
        assert 0.0 <= new_val <= 1.0
        assert abs(new_val - 0.59) < 0.01

    def test_confidence_decays_with_difficulty(self):
        monitor = MetacognitiveMonitor()
        state = monitor.track("t1", performance=0.5, expected_difficulty=1.0)
        assert state.overall < 0.6
