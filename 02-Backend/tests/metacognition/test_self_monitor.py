from metacognition.self_monitor import SelfMonitor, HealthMetric, MonitorReport


def test_record_metric():
    monitor = SelfMonitor()
    metric = monitor.record_metric("cpu", 0.8, 1000.0, threshold_high=0.9)
    assert metric.value == 0.8
    assert metric.name == "cpu"


def test_set_baseline():
    monitor = SelfMonitor()
    monitor.set_baseline("cpu", 0.9)
    assert monitor.baselines["cpu"] == 0.9


def test_get_recent():
    monitor = SelfMonitor()
    monitor.record_metric("cpu", 0.8, 1000.0)
    monitor.record_metric("cpu", 0.7, 2000.0)
    recent = monitor.get_recent("cpu", count=1)
    assert len(recent) == 1
    assert recent[0].value == 0.7


def test_detect_degradation_true():
    monitor = SelfMonitor()
    monitor.set_baseline("cpu", 0.9)
    for i in range(10):
        monitor.record_metric("cpu", 0.5, float(1000 + i))
    assert monitor.detect_degradation("cpu", tolerance=0.2)


def test_detect_degradation_false():
    monitor = SelfMonitor()
    monitor.set_baseline("cpu", 0.9)
    for i in range(10):
        monitor.record_metric("cpu", 0.9, float(1000 + i))
    assert not monitor.detect_degradation("cpu", tolerance=0.2)


def test_calculate_health_score():
    monitor = SelfMonitor()
    for i in range(5):
        monitor.record_metric("cpu", 0.7 + 0.1 * i, float(1000 + i))
    score = monitor.calculate_health_score("cpu")
    assert 0.0 <= score <= 1.0


def test_get_alerts_low():
    monitor = SelfMonitor()
    monitor.record_metric("cpu", 0.1, 1000.0, threshold_low=0.3)
    alerts = monitor.get_alerts("cpu")
    assert len(alerts) > 0
    assert "Low cpu" in alerts[0]


def test_get_alerts_high():
    monitor = SelfMonitor()
    monitor.record_metric("cpu", 0.95, 1000.0, threshold_high=0.9)
    alerts = monitor.get_alerts("cpu")
    assert len(alerts) > 0
    assert "High cpu" in alerts[0]


def test_generate_report_healthy():
    monitor = SelfMonitor()
    for i in range(10):
        monitor.record_metric("cpu", 0.9, float(1000 + i))
    report = monitor.generate_report()
    assert report.healthy
    assert report.overall_score > 0.0


def test_generate_report_degraded():
    monitor = SelfMonitor()
    monitor.set_baseline("cpu", 0.9)
    for i in range(10):
        monitor.record_metric("cpu", 0.5, float(1000 + i))
    report = monitor.generate_report()
    assert not report.healthy
    assert "cpu" in report.degraded_metrics


def test_get_metric_summary():
    monitor = SelfMonitor()
    for i in range(5):
        monitor.record_metric("cpu", 0.5 + 0.1 * i, float(1000 + i))
    summary = monitor.get_metric_summary("cpu")
    assert "current" in summary
    assert "average" in summary
    assert summary["min"] == 0.5
    assert summary["max"] == 0.9
