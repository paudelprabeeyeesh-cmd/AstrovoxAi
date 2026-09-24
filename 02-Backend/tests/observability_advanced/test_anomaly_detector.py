
import pytest

from advanced_backend.observability_advanced.anomaly_detector import AnomalyDetector


def test_detect_insufficient_data():
    detector = AnomalyDetector()
    result = detector.detect("m", 1.0)
    assert result["anomaly"] is False
    assert result["reason"] == "insufficient_data"


def test_detect_no_anomaly_within_range():
    detector = AnomalyDetector(threshold=3.0)
    for value in [10.0, 11.0, 10.5, 12.0]:
        detector.record("m", value)
    result = detector.detect("m", 11.0)
    assert result["anomaly"] is False
    assert result["z_score"] == pytest.approx(0.14638501094227999)


def test_detect_anomaly_above_threshold():
    detector = AnomalyDetector(threshold=2.0)
    for value in [10.0, 11.0, 10.5]:
        detector.record("m", value)
    result = detector.detect("m", 100.0)
    assert result["anomaly"] is True
    assert result["z_score"] > 2.0


def test_detect_zero_stdev():
    detector = AnomalyDetector()
    detector.record("m", 5.0)
    detector.record("m", 5.0)
    result = detector.detect("m", 5.0)
    assert result["z_score"] == 0.0
    assert result["anomaly"] is False


def test_record_creates_history():
    detector = AnomalyDetector()
    detector.record("m", 1.0)
    detector.record("m", 2.0)
    assert len(detector._history["m"]) == 2
