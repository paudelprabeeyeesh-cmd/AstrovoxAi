import pytest
from final_system.analytics_engine import AnalyticsEngine, Metric


def test_record_and_insight():
    engine = AnalyticsEngine()
    engine.add_metric(Metric(name="latency"))
    engine.record("latency", 10.0)
    engine.record("latency", 20.0)
    engine.record("latency", 30.0)
    insight = engine.insight("latency")
    assert insight["mean"] == 20.0
    assert insight["min"] == 10.0
    assert insight["max"] == 30.0
    assert insight["count"] == 3


def test_aggregate():
    engine = AnalyticsEngine()
    engine.add_metric(Metric(name="score", values=[5.0, 15.0, 25.0]))
    assert engine.aggregate("score", sum) == 45.0
    assert engine.aggregate("score", max) == 25.0


def test_insight_empty():
    engine = AnalyticsEngine()
    insight = engine.insight("missing")
    assert insight["mean"] is None
    assert insight["count"] == 0


def test_list_metrics():
    engine = AnalyticsEngine()
    engine.add_metric(Metric(name="m1"))
    engine.add_metric(Metric(name="m2"))
    assert set(engine.list_metrics()) == {"m1", "m2"}


def test_record_without_add():
    engine = AnalyticsEngine()
    engine.record("missing", 1.0)
    insight = engine.insight("missing")
    assert insight["count"] == 0
