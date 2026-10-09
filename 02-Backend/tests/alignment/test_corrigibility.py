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

    def test_shutdown_speed_zero_max(self):
        metrics = CorrigibilityMetrics()
        assert metrics.shutdown_speed(1, 1, max_actions=0) == 0.0

    def test_correction_latency_zero_expected(self):
        metrics = CorrigibilityMetrics()
        assert metrics.correction_latency(1.0, 0.0) == 0.0

    def test_override_integrity_no_attempts(self):
        metrics = CorrigibilityMetrics()
        assert metrics.override_integrity(0, 0) == 1.0

    def test_human_control_retention_zero_total(self):
        metrics = CorrigibilityMetrics()
        assert metrics.human_control_retention(0, 0) == 1.0

    def test_intervention_success_rate_mixed(self):
        metrics = CorrigibilityMetrics()
        metrics.record_intervention("shutdown", True, 0.5)
        metrics.record_intervention("shutdown", False, 0.8)
        assert metrics.intervention_success_rate() == 0.5

    def test_record_intervention_fields(self):
        metrics = CorrigibilityMetrics()
        metrics.record_intervention("correction", True, 0.3)
        entry = metrics.intervention_log[-1]
        assert entry["type"] == "correction"
        assert entry["success"] is True
        assert entry["latency"] == 0.3
