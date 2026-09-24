import pytest
from emergent_abilities.capability_suddenness import (
    CapabilitySuddennessDetector,
    CapabilitySuddennessReport,
    EmergenceCapabilityTracker,
    _mean,
    _smooth,
)


class TestMean:
    def test_mean_normal(self):
        assert _mean([1.0, 2.0, 3.0, 4.0]) == pytest.approx(2.5)

    def test_mean_single(self):
        assert _mean([5.0]) == pytest.approx(5.0)

    def test_mean_empty(self):
        assert _mean([]) == 0.0

    def test_mean_negative(self):
        assert _mean([-1.0, 1.0]) == pytest.approx(0.0)


class TestSmooth:
    def test_smooth_no_window(self):
        values = [1.0, 2.0, 3.0]
        result = _smooth(values, 1)
        assert result == [1.0, 2.0, 3.0]

    def test_smooth_window_3(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _smooth(values, 3)
        assert len(result) == 5

    def test_smooth_short_series(self):
        values = [1.0, 2.0]
        result = _smooth(values, 5)
        assert result == [1.0, 2.0]

    def test_smooth_preserves_length(self):
        values = [float(i) for i in range(10)]
        result = _smooth(values, 3)
        assert len(result) == len(values)


class TestCapabilitySuddennessReport:
    def test_creation(self):
        report = CapabilitySuddennessReport(
            capability_name="math",
            threshold=7.0,
            pre_performance=0.1,
            post_performance=0.8,
            suddenness=0.7,
            supporting_evidence=["jump at 7B"],
        )
        assert report.capability_name == "math"
        assert report.suddenness == 0.7
        assert len(report.supporting_evidence) == 1

    def test_fields(self):
        report = CapabilitySuddennessReport(
            capability_name="code",
            threshold=3.0,
            pre_performance=0.0,
            post_performance=0.5,
            suddenness=0.5,
            supporting_evidence=[],
        )
        assert report.threshold == 3.0
        assert report.post_performance == 0.5


class TestCapabilitySuddennessDetector:
    def test_initialization(self):
        detector = CapabilitySuddennessDetector()
        assert detector.smoothing_window == 3
        assert detector.suddenness_threshold == 0.3

    def test_custom_threshold(self):
        detector = CapabilitySuddennessDetector(suddenness_threshold=0.6)
        assert detector.suddenness_threshold == 0.6

    def test_detect_single_point(self):
        detector = CapabilitySuddennessDetector()
        report = detector.detect_sudden_jump([5.0], [0.3], "lang")
        assert report.capability_name == "lang"
        assert report.suddenness == 0.0
        assert "insufficient data points" in report.supporting_evidence

    def test_detect_sudden_jump_gradual(self):
        detector = CapabilitySuddennessDetector()
        sizes = [1.0, 3.0, 5.0, 7.0, 9.0]
        perfs = [0.3, 0.3, 0.3, 0.32, 0.32]
        report = detector.detect_sudden_jump(sizes, perfs)
        assert report.suddenness < 0.3

    def test_detect_sudden_jump_sharp(self):
        detector = CapabilitySuddennessDetector(smoothing_window=1)
        sizes = [1.0, 2.0, 3.0, 4.0, 5.0]
        perfs = [0.05, 0.05, 0.05, 0.90, 0.92]
        report = detector.detect_sudden_jump(sizes, perfs, "code")
        assert report.capability_name == "code"
        assert report.suddenness > 0.3
        assert report.threshold == 4.0
        assert report.post_performance > report.pre_performance

    def test_detect_flat_performance(self):
        detector = CapabilitySuddennessDetector()
        sizes = [1.0, 2.0, 3.0]
        perfs = [0.5, 0.5, 0.5]
        report = detector.detect_sudden_jump(sizes, perfs)
        assert report.suddenness == pytest.approx(0.0)

    def test_analyze_all_capabilities(self):
        detector = CapabilitySuddennessDetector()
        model_sizes = [1.0, 3.0, 7.0, 13.0]
        capability_data = {
            "math": [0.1, 0.15, 0.85, 0.9],
            "code": [0.05, 0.05, 0.05, 0.90],
        }
        reports = detector.analyze_all_capabilities(model_sizes, capability_data)
        assert len(reports) == 2
        names = {r.capability_name for r in reports}
        assert names == {"math", "code"}

    def test_analyze_mismatched_length_skipped(self):
        detector = CapabilitySuddennessDetector()
        model_sizes = [1.0, 2.0, 3.0]
        capability_data = {
            "short": [0.1, 0.2],
            "full": [0.1, 0.2, 0.9],
        }
        reports = detector.analyze_all_capabilities(model_sizes, capability_data)
        assert len(reports) == 1
        assert reports[0].capability_name == "full"

    def test_detect_gradual_vs_sudden_sudden(self):
        detector = CapabilitySuddennessDetector()
        result = detector.detect_gradual_vs_sudden(
            [1.0, 2.0, 3.0, 4.0, 5.0],
            [0.05, 0.05, 0.05, 0.90, 0.92],
        )
        assert result["regime"] == "sudden"
        assert "threshold" in result

    def test_detect_gradual_vs_sudden_gradual(self):
        detector = CapabilitySuddennessDetector()
        result = detector.detect_gradual_vs_sudden(
            [1.0, 2.0, 3.0, 4.0, 5.0],
            [0.3, 0.3, 0.3, 0.32, 0.32],
        )
        assert result["regime"] == "gradual"


class TestEmergenceCapabilityTracker:
    def test_initialization(self):
        tracker = EmergenceCapabilityTracker()
        assert tracker.emergence_history == []

    def test_track_emergence(self):
        tracker = EmergenceCapabilityTracker()
        report = tracker.track_emergence(
            "math",
            [1.0, 3.0, 7.0, 13.0],
            [0.1, 0.15, 0.85, 0.9],
        )
        assert report.capability_name == "math"
        assert len(tracker.emergence_history) == 1
        assert tracker.emergence_history[0]["capability"] == "math"

    def test_emergence_rate_empty(self):
        tracker = EmergenceCapabilityTracker()
        assert tracker.emergence_rate() == 0.0

    def test_emergence_rate_with_data(self):
        tracker = EmergenceCapabilityTracker()
        tracker.track_emergence("a", [1.0, 2.0, 5.0], [0.1, 0.1, 0.8])
        tracker.track_emergence("b", [1.0, 2.0, 5.0], [0.05, 0.05, 0.90])
        rate = tracker.emergence_rate()
        assert 0.0 <= rate <= 1.0

    def test_capability_order_by_threshold(self):
        tracker = EmergenceCapabilityTracker()
        tracker.track_emergence("large", [10.0, 20.0, 30.0], [0.1, 0.1, 0.8])
        tracker.track_emergence("small", [1.0, 2.0, 3.0], [0.1, 0.2, 0.9])
        order = tracker.capability_order_by_threshold()
        assert order == ["small", "large"]

    def test_sudden_capabilities_all(self):
        tracker = EmergenceCapabilityTracker()
        tracker.track_emergence("sudden_1", [1.0, 5.0], [0.05, 0.95])
        tracker.track_emergence("sudden_2", [1.0, 5.0], [0.05, 0.90])
        tracker.track_emergence("gradual", [1.0, 5.0], [0.3, 0.32])
        sudden = tracker.sudden_capabilities(threshold=0.3)
        assert "sudden_1" in sudden
        assert "sudden_2" in sudden
        assert "gradual" not in sudden

    def test_sudden_capabilities_none(self):
        tracker = EmergenceCapabilityTracker()
        tracker.track_emergence("gradual_1", [1.0, 5.0], [0.3, 0.32])
        tracker.track_emergence("gradual_2", [1.0, 5.0], [0.5, 0.52])
        sudden = tracker.sudden_capabilities(threshold=0.8)
        assert sudden == []
