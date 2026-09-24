from simulation_engine.metrics_collector import MetricsCollector


def test_record_and_summary():
    mc = MetricsCollector()
    mc.record("latency", 0.1)
    mc.record("latency", 0.3)
    mc.record("latency", 0.5)
    s = mc.summary("latency")
    assert s["count"] == 3.0
    assert s["mean"] == 0.3
    assert s["min"] == 0.1
    assert s["max"] == 0.5


def test_summary_empty():
    mc = MetricsCollector()
    assert mc.summary("missing") == {}


def test_all_time_series():
    mc = MetricsCollector()
    mc.record("success", 1.0)
    ts = mc.all_time_series()
    assert ts["success"] == [1.0]
