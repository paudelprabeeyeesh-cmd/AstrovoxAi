from services.metrics_service import MetricsService


class TestMetricsService:
    def test_increment_counter(self):
        svc = MetricsService()
        svc.increment("requests", 1)
        svc.increment("requests", 2)
        metrics = svc.get_metrics()
        assert metrics["counters"]["requests"] == 3.0

    def test_gauge_value(self):
        svc = MetricsService()
        svc.gauge("memory", 128.5)
        metrics = svc.get_metrics()
        assert metrics["gauges"]["memory"] == 128.5

    def test_default_counter_is_zero(self):
        svc = MetricsService()
        metrics = svc.get_metrics()
        assert metrics["counters"] == {}

    def test_gauge_overwrite(self):
        svc = MetricsService()
        svc.gauge("temperature", 20.0)
        svc.gauge("temperature", 25.0)
        metrics = svc.get_metrics()
        assert metrics["gauges"]["temperature"] == 25.0
