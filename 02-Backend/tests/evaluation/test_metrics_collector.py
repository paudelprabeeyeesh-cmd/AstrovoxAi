from evaluation.metrics_collector import MetricsCollector, MetricSnapshot


def test_metrics_collector_record_and_summary():
    collector = MetricsCollector()
    collector.record("latency", 0.1)
    collector.record("latency", 0.2)
    collector.record("latency", 0.3)
    summary = collector.summary("latency")
    assert summary["count"] == 3
    assert abs(summary["mean"] - 0.2) < 1e-9
    assert summary["min"] == 0.1
    assert summary["max"] == 0.3


def test_metrics_collector_stddev():
    collector = MetricsCollector()
    collector.record("x", 1.0)
    collector.record("x", 2.0)
    summary = collector.summary("x")
    assert "stddev" in summary


def test_metrics_collector_snapshots():
    collector = MetricsCollector()
    collector.record("cpu", 0.5, metadata={"host": "a"})
    snapshots = collector.snapshots("cpu")
    assert len(snapshots) == 1
    assert snapshots[0].name == "cpu"
    assert snapshots[0].metadata == {"host": "a"}


def test_metrics_collector_all_summaries():
    collector = MetricsCollector()
    collector.record("a", 1.0)
    collector.record("b", 2.0)
    summaries = collector.all_summaries()
    assert "a" in summaries
    assert "b" in summaries


def test_metrics_collector_reset():
    collector = MetricsCollector()
    collector.record("x", 1.0)
    collector.reset("x")
    assert collector.summary("x") == {}
    collector.record("y", 2.0)
    collector.reset()
    assert collector.all_summaries() == {}
