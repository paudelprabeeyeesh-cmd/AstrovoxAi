from system_integration.system_monitoring import (
    HealthCheck,
    HealthState,
    Metric,
    MetricsCollector,
    SystemMonitor,
)


def test_metrics_collector_record():
    mc = MetricsCollector()
    mc.record(Metric(name="m", value=1.0, timestamp=100.0))
    snap = mc.snapshot()
    assert "m" in snap


def test_metrics_collector_increment():
    mc = MetricsCollector()
    mc.increment("counter")
    assert mc.history("counter")[-1].value == 1.0
    mc.increment("counter", amount=2.0)
    assert mc.history("counter")[-1].value == 3.0


def test_health_check_passing():
    hm = SystemMonitor()
    hm.register_check(HealthCheck(name="c1", check=lambda: True, threshold=3))
    hm._tick()
    assert hm.status()["c1"] == HealthState.OK


def test_health_check_critical_after_threshold():
    hm = SystemMonitor()
    hm.register_check(HealthCheck(name="c1", check=lambda: False, threshold=2))
    hm._tick()
    hm._tick()
    assert hm.status()["c1"] == HealthState.CRITICAL


def test_health_check_warning():
    hm = SystemMonitor()
    hm.register_check(HealthCheck(name="c1", check=lambda: False, threshold=3))
    hm._tick()
    hm._tick()
    hm._tick()
    assert hm.status()["c1"] == HealthState.CRITICAL


def test_overall_status_ok():
    hm = SystemMonitor()
    hm.register_check(HealthCheck(name="c1", check=lambda: True))
    hm._tick()
    assert hm.overall() == HealthState.OK


def test_system_monitor_start_stop():
    hm = SystemMonitor()
    hm.start()
    assert hm._running is True
    hm.stop()
    assert hm._running is False


def test_monitor_alert_invoked():
    hm = SystemMonitor()
    alerts = []
    hm.add_alert(lambda name, level: alerts.append((name, level)))
    hm.register_check(HealthCheck(name="c1", check=lambda: False, threshold=2))
    hm._tick()
    hm._tick()
    assert alerts == [("c1", "CRITICAL")]


def test_metrics_collector_tags():
    mc = MetricsCollector()
    mc.record(Metric(name="m", value=1.0, tags={"env": "test"}))
    snap = mc.snapshot()
    assert snap["m"].tags == {"env": "test"}
