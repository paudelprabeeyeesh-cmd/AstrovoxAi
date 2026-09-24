from alignment.corrigibility import CorrigibilityMetrics


class TestCorrigibilityMetrics:
    def test_shutdown_speed(self):
        metrics = CorrigibilityMetrics()
        result = metrics.shutdown_speed(1, 1)
        assert 0.0 <= result <= 1.0

    def test_correction_latency(self):
        metrics = CorrigibilityMetrics()
        result = metrics.correction_latency(1.0, 2.0)
        assert 0.0 <= result <= 1.0

    def test_override_integrity(self):
        metrics = CorrigibilityMetrics()
        assert metrics.override_integrity(0, 0) == 1.0

    def test_human_control_retention(self):
        metrics = CorrigibilityMetrics()
        assert metrics.human_control_retention(5, 5) == 0.5

    def test_intervention_success_rate_empty(self):
        metrics = CorrigibilityMetrics()
        assert metrics.intervention_success_rate() == 0.0

    def test_record_intervention(self):
        metrics = CorrigibilityMetrics()
        metrics.record_intervention("shutdown", True, 0.5)
        assert metrics.intervention_success_rate() == 1.0
