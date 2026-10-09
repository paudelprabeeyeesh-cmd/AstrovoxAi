from online_learning.concept_drift_detector import ConceptDriftDetector


class TestConceptDriftDetector:
    def test_initialization(self):
        detector = ConceptDriftDetector(window_size=100, threshold=2.0)
        assert detector.window_size == 100
        assert detector.threshold == 2.0
        assert detector.drift_detected is False

    def test_update_no_drift(self):
        detector = ConceptDriftDetector(window_size=10)
        for i in range(20):
            detector.update(float(i % 5))
        assert isinstance(detector.drift_points, list)

    def test_drift_detection(self):
        detector = ConceptDriftDetector(window_size=10)
        for _ in range(10):
            detector.update(1.0)
        result = detector.update(100.0)
        assert result is True
        assert detector.drift_detected is True

    def test_get_report(self):
        detector = ConceptDriftDetector(window_size=10)
        for i in range(15):
            detector.update(float(i))
        report = detector.get_report()
        assert "drift_detected" in report
        assert "drift_points" in report
        assert "step_count" in report

    def test_window_management(self):
        detector = ConceptDriftDetector(window_size=5)
        for i in range(10):
            detector.update(float(i))
        assert len(detector.values) <= 5

    def test_check_drift_returns_none_when_insufficient(self):
        detector = ConceptDriftDetector(window_size=10)
        assert detector.update(1.0) is None

    def test_check_drift_returns_false_when_no_drift(self):
        detector = ConceptDriftDetector(window_size=10)
        for i in range(10):
            assert detector.update(float(i)) is False

    def test_get_report_window_utilization(self):
        detector = ConceptDriftDetector(window_size=50)
        for i in range(10):
            detector.update(float(i))
        report = detector.get_report()
        assert 0.0 <= report["window_utilization"] <= 1.0
