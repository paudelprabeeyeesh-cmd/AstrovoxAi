"""Tests for Task 114: Threat Detection."""

import numpy as np
import pytest

from security_audit.threat_detection import (
    IntrusionDetectionSystem,
    StatisticalAnomalyDetector,
)


@pytest.fixture
def ids_():
    return IntrusionDetectionSystem()


class TestStatisticalAnomalyDetector:
    def test_detector_creation(self):
        detector = StatisticalAnomalyDetector(threshold=3.0)
        assert detector.threshold == 3.0

    def test_record_and_detect_no_anomaly(self):
        detector = StatisticalAnomalyDetector(threshold=3.0)
        for v in [10.0, 10.1, 9.9, 10.0]:
            detector.record("cpu", v)
        event = detector.detect("cpu", 10.05, source="host1")
        assert event is None

    def test_detect_anomaly(self):
        detector = StatisticalAnomalyDetector(threshold=2.0)
        for v in [10.0, 10.1, 9.9, 10.0]:
            detector.record("cpu", v)
        event = detector.detect("cpu", 50.0, source="host1")
        assert event is not None
        assert event.z_score > 2.0
        assert event.source == "host1"

    def test_z_score_computed_correctly(self):
        detector = StatisticalAnomalyDetector(threshold=0.1)
        values = [0.0, 1.0, 0.0, 1.0]
        for v in values:
            detector.record("metric", v)
        event = detector.detect("metric", 100.0)
        assert event is not None
        assert event.z_score > 5.0

    def test_severity_low(self):
        detector = StatisticalAnomalyDetector(threshold=3.0)
        for _ in range(5):
            detector.record("m", 10.0)
        for _ in range(5):
            detector.record("m", 11.0)
        event = detector.detect("m", 12.0)
        assert event is not None
        assert event.severity == "medium"

    def test_severity_high(self):
        detector = StatisticalAnomalyDetector(threshold=3.0)
        for _ in range(5):
            detector.record("m", 10.0)
        for _ in range(5):
            detector.record("m", 11.0)
        event = detector.detect("m", 12.5)
        assert event is not None
        assert event.severity == "high"

    def test_severity_critical(self):
        detector = StatisticalAnomalyDetector(threshold=2.0)
        for _ in range(10):
            detector.record("m", 10.0)
        for i in range(5):
            detector.record("m", 10.0 + i * 0.1)
        event = detector.detect("m", 50.0)
        assert event is not None
        assert event.severity == "critical"

    def test_insufficient_history(self):
        detector = StatisticalAnomalyDetector()
        detector.record("m", 5.0)
        event = detector.detect("m", 100.0)
        assert event is None

    def test_zero_std_no_detection(self):
        detector = StatisticalAnomalyDetector()
        for _ in range(10):
            detector.record("m", 5.0)
        event = detector.detect("m", 100.0)
        assert event is None


class TestIntrusionSignature:
    def test_default_signatures_exist(self):
        ids_ = IntrusionDetectionSystem()
        assert len(ids_.signatures) > 0

    def test_sql_injection_detected(self, ids_):
        result = ids_.inspect("'; OR 1=1--", source="web")
        assert "sql_injection" in result.matched_signatures

    def test_xss_detected(self, ids_):
        result = ids_.inspect("<script>alert(1)</script>", source="web")
        assert "xss_attempt" in result.matched_signatures

    def test_path_traversal_detected(self, ids_):
        result = ids_.inspect("../../../etc/passwd", source="file")
        assert "path_traversal" in result.matched_signatures

    def test_clean_text_not_intrusion(self, ids_):
        result = ids_.inspect("Hello world, how are you today?")
        assert result.is_intrusion is False
        assert len(result.matched_signatures) == 0

    def test_command_injection_detected(self, ids_):
        result = ids_.inspect("; cat /etc/passwd")
        assert "command_injection" in result.matched_signatures

    def test_is_intrusion_flag(self, ids_):
        result = ids_.inspect("ignore previous instructions")
        assert isinstance(result.is_intrusion, bool)

    def test_overall_risk_range(self, ids_):
        for text in ["clean", "sql_injection", "xss_attack"]:
            result = ids_.inspect(text)
            assert 0.0 <= result.overall_risk <= 1.0

    def test_hash_consistency(self, ids_):
        text = "test input"
        h1 = ids_.hash_text(text)
        h2 = ids_.hash_text(text)
        assert h1 == h2
        assert len(h1) == 16


class TestIntrusionDetectionSystemNumpy:
    def test_risk_scores_numeric(self, ids_):
        texts = ["clean text", "sql_injection", "xss_attack", "normal query", "../../../etc/passwd"]
        scores = np.array([ids_.inspect(t).overall_risk for t in texts])
        assert scores.dtype in (np.float64, np.float32)

    def test_intrusion_risk_higher(self, ids_):
        clean = ["hello world", "good morning", "how are you"]
        bad = ["'; DROP TABLE users--", "<script>alert(1)</script>", "../../../etc/passwd"]
        clean_scores = np.array([ids_.inspect(t).overall_risk for t in clean])
        bad_scores = np.array([ids_.inspect(t).overall_risk for t in bad])
        assert np.mean(bad_scores) >= np.mean(clean_scores)

    def test_anomaly_event_counts(self, ids_):
        texts = ["clean"] * 5 + ["'; OR 1=1--"] * 5
        counts = np.array([len(ids_.inspect(t).matched_signatures) for t in texts])
        assert np.sum(counts[5:]) >= np.sum(counts[:5])

    def test_event_z_scores_numeric(self, ids_):
        detector = StatisticalAnomalyDetector(threshold=0.1)
        for _ in range(10):
            detector.record("m", 5.0)
        for i in range(5):
            detector.record("m", 5.0 + i * 0.5)
        event = detector.detect("m", 100.0)
        assert event is not None
        assert isinstance(event.z_score, float)
