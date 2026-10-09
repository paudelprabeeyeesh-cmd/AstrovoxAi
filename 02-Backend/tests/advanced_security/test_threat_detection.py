import hashlib
import hmac
from advanced_security.post_quantum_crypto import LatticeSignature
from advanced_security.threat_detection import (
    AnomalyDetector,
    BruteForceDetector,
    PortScanDetector,
    SignatureDetector,
    ThreatDetector,
    ThreatEvent,
)


def test_anomaly_detector_no_anomaly() -> None:
    detector = AnomalyDetector()
    for i in range(20):
        assert detector.observe(1.0) is None


def test_anomaly_detector_outlier() -> None:
    detector = AnomalyDetector(threshold=2.0)
    for i in range(20):
        detector.observe(1.0)
    hit = detector.observe(100.0)
    assert hit is not None
    assert hit["z_score"] > 2.0


def test_brute_force_detector() -> None:
    detector = BruteForceDetector(window=60, threshold=3)
    for _ in range(2):
        assert detector.record("10.0.0.1") is None
    hit = detector.record("10.0.0.1")
    assert hit is not None
    assert hit["attempts"] == 3


def test_port_scan_detector() -> None:
    detector = PortScanDetector(window=60, unique_threshold=5)
    for port in range(4):
        assert detector.record("10.0.0.1", port) is None
    hit = detector.record("10.0.0.1", 4)
    assert hit is not None
    assert hit["unique_ports"] == 5


def test_signature_detector_match() -> None:
    detector = SignatureDetector()
    detector.add_signature("sql_injection", r"SELECT\s+.*\s+FROM", severity=0.9)
    matches = detector.scan("SELECT * FROM users")
    assert len(matches) == 1
    assert matches[0]["name"] == "sql_injection"


def test_signature_detector_no_match() -> None:
    detector = SignatureDetector()
    detector.add_signature("sql_injection", r"SELECT\s+.*\s+FROM")
    matches = detector.scan("hello world")
    assert len(matches) == 0


def test_threat_detector_unified() -> None:
    detector = ThreatDetector()
    for i in range(20):
        detector.observe_value("source1", 1.0)
    event = detector.observe_value("source1", 100.0)
    assert event is not None
    assert event.event_type == "anomaly"


def test_threat_detector_brute_force() -> None:
    detector = ThreatDetector()
    for _ in range(2):
        detector.record_auth("10.0.0.1")
    event = detector.record_auth("10.0.0.1")
    assert event is not None
    assert event.event_type == "brute_force"


def test_threat_detector_recent_events() -> None:
    detector = ThreatDetector()
    detector.record_auth("10.0.0.1")
    for _ in range(4):
        detector.record_auth("10.0.0.1")
    recent = detector.recent_events(limit=10)
    assert len(recent) == 5
