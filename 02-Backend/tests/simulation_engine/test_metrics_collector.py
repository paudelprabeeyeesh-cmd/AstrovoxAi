from simulation_engine.metrics_collector import MetricsCollector, MetricSample


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


def test_metric_sample_dataclass():
    sample = MetricSample(name="loss", value=0.5, timestamp=100.0, tags={"env": "test"})
    assert sample.name == "loss"
    assert sample.value == 0.5
    assert sample.timestamp == 100.0
    assert sample.tags == {"env": "test"}


def test_record_with_tags():
    mc = MetricsCollector()
    mc.record("loss", 0.5, tags={"env": "train"})
    assert mc._samples["loss"] == [0.5]


def test_summary_single_value():
    mc = MetricsCollector()
    mc.record("accuracy", 0.9)
    s = mc.summary("accuracy")
    assert s["count"] == 1.0
    assert s["mean"] == 0.9
    assert s["min"] == 0.9
    assert s["max"] == 0.9


def test_all_time_series_returns_copy():
    mc = MetricsCollector()
    mc.record("metric", 1.0)
    ts1 = mc.all_time_series()
    ts1["new_metric"] = [2.0]
    ts2 = mc.all_time_series()
    assert "new_metric" not in ts2


def test_multiple_metrics():
    mc = MetricsCollector()
    mc.record("loss", 0.1)
    mc.record("accuracy", 0.9)
    assert mc.summary("loss") == {"count": 1.0, "mean": 0.1, "min": 0.1, "max": 0.1}
    assert mc.summary("accuracy") == {"count": 1.0, "mean": 0.9, "min": 0.9, "max": 0.9}
