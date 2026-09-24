from dataclasses import dataclass

from performance_optimization.hotspot_detector import (
    HotspotReport,
    detect_hotspots,
    hotspot_summary,
    to_json,
)


@dataclass
class DummyRecord:
    name: str
    iterations: int
    total_seconds: float
    per_iteration_ms: float


def test_detect_hotspots_filters_below_threshold():
    records = [
        DummyRecord("fast", 1, 0.001, 1.0),
        DummyRecord("slow", 1, 0.1, 100.0),
    ]
    report = detect_hotspots(records, threshold_ms=10.0)
    assert len(report.ranked) == 1
    assert report.ranked[0]["name"] == "slow"
    assert report.hotspot_ms == 100.0


def test_detect_hotspots_empty_when_all_below_threshold():
    records = [
        DummyRecord("a", 1, 0.001, 1.0),
        DummyRecord("b", 1, 0.001, 2.0),
    ]
    report = detect_hotspots(records, threshold_ms=10.0)
    assert report.ranked == []
    assert report.hotspot_ms == 0.0


def test_detect_hotspots_sorted_descending():
    records = [
        DummyRecord("a", 1, 0.1, 50.0),
        DummyRecord("b", 1, 0.1, 100.0),
    ]
    report = detect_hotspots(records, threshold_ms=10.0)
    assert [e["name"] for e in report.ranked] == ["b", "a"]


def test_hotspot_summary_contains_threshold():
    records = [DummyRecord("x", 1, 0.1, 10.0)]
    report = detect_hotspots(records, threshold_ms=10.0)
    summary = hotspot_summary(report)
    assert "Threshold: 10.000 ms" in summary
    assert "x: 10.000 ms" in summary


def test_to_json_returns_string():
    records = [DummyRecord("x", 1, 0.1, 10.0)]
    report = detect_hotspots(records, threshold_ms=10.0)
    json_str = to_json(report)
    assert "threshold_ms" in json_str
    assert "ranked" in json_str
