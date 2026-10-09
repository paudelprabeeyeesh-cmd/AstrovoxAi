
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


def test_detect_exactly_two_points():
    detector = AnomalyDetector(threshold=2.0)
    detector.record("m", 10.0)
    detector.record("m", 20.0)
    result = detector.detect("m", 100.0)
    assert result["anomaly"] is True
    assert result["z_score"] > 2.0


def test_multiple_metrics_independent():
    detector = AnomalyDetector()
    detector.record("cpu", [80.0, 82.0, 81.0])
    detector.record("mem", [4.0, 4.0, 4.0])
    cpu_result = detector.detect("cpu", 200.0)
    mem_result = detector.detect("mem", 10.0)
    assert cpu_result["anomaly"] is True
    assert mem_result["anomaly"] is False
    assert cpu_result["metric"] == "cpu"
    assert mem_result["metric"] == "mem"


def test_custom_threshold_used():
    detector = AnomalyDetector(threshold=1.0)
    detector.record("m", [10.0, 10.0, 10.0])
    result = detector.detect("m", 20.0)
    assert result["z_score"] > 1.0
    assert result["anomaly"] is True
