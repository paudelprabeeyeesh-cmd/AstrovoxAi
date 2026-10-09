from ..self_healing import SelfHealing


class TestSelfHealing:
    def test_register_handler(self):
        sh = SelfHealing()
        sh.register_handler("db", lambda c: None)
        assert "db" in sh.handlers

    def test_healthy_check(self):
        sh = SelfHealing()
        assert sh.check_health("api", True, "ok") is True
        assert len(sh.checks) == 1

    def test_unhealthy_triggers_recovery(self):
        sh = SelfHealing()
        recovered = []
        sh.register_handler("svc", lambda c: recovered.append(c))
        result = sh.check_health("svc", False)
        assert result is False
        assert recovered == ["svc"]

    def test_max_retries_limits_recovery(self):
        sh = SelfHealing(max_retries=2)
        sh.check_health("svc", False)
        sh.check_health("svc", False)
        sh.check_health("svc", False)
        assert sh.retry_counts.get("svc", 0) == 2

    def test_health_summary(self):
        sh = SelfHealing()
        sh.check_health("a", True)
        sh.check_health("b", False)
        summary = sh.get_health_summary()
        assert summary["total_checks"] == 2
        assert summary["healthy"] == 1
        assert summary["unhealthy"] == 1
