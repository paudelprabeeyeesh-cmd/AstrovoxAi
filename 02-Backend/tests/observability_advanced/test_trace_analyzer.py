import pytest

from advanced_backend.observability_advanced import Span
from advanced_backend.observability_advanced.trace_analyzer import TraceAnalyzer


def test_analyze_empty_trace():
    analyzer = TraceAnalyzer()
    result = analyzer.analyze("t1")
    assert result == {"trace_id": "t1", "span_count": 0}


def test_analyze_trace_with_spans():
    analyzer = TraceAnalyzer()
    spans = [
        Span(name="a", trace_id="t1", span_id="s1", parent_id=None, start_time=0.0, end_time=0.1),
        Span(name="b", trace_id="t1", span_id="s2", parent_id="s1", start_time=0.05, end_time=0.2),
    ]
    analyzer.add_trace("t1", spans)
    result = analyzer.analyze("t1")
    assert result["trace_id"] == "t1"
    assert result["span_count"] == 2
    assert result["operations"] == ["a", "b"]
    assert result["duration_stats"]["mean"] == pytest.approx(125.0)
    assert result["duration_stats"]["max"] == pytest.approx(150.0)
    assert result["duration_stats"]["min"] == pytest.approx(100.0)
    assert result["duration_stats"]["median"] == pytest.approx(125.0)


def test_analyze_ignores_open_spans():
    analyzer = TraceAnalyzer()
    spans = [
        Span(name="a", trace_id="t1", span_id="s1", parent_id=None, start_time=0.0, end_time=0.1),
        Span(name="b", trace_id="t1", span_id="s2", parent_id="s1", start_time=0.05),
    ]
    analyzer.add_trace("t1", spans)
    result = analyzer.analyze("t1")
    assert result["span_count"] == 2
    assert result["duration_stats"]["mean"] == pytest.approx(100.0)


def test_add_trace_extends_existing():
    analyzer = TraceAnalyzer()
    analyzer.add_trace("t1", [
        Span(name="a", trace_id="t1", span_id="s1", parent_id=None, start_time=0.0, end_time=0.1),
    ])
    analyzer.add_trace("t1", [
        Span(name="b", trace_id="t1", span_id="s2", parent_id="s1", start_time=0.0, end_time=0.2),
    ])
    result = analyzer.analyze("t1")
    assert result["span_count"] == 2
    assert result["operations"] == ["a", "b"]
