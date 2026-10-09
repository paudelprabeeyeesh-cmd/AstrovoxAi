from unittest.mock import MagicMock, patch



class TestHealthStatus:
    def test_healthy_value(self):
        from app.health import HealthStatus

        assert HealthStatus.HEALTHY.value == "healthy"

    def test_degraded_value(self):
        from app.health import HealthStatus

        assert HealthStatus.DEGRADED.value == "degraded"

    def test_unhealthy_value(self):
        from app.health import HealthStatus

        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestComponentHealth:
    def test_default_latency(self):
        from app.health import ComponentHealth, HealthStatus

        c = ComponentHealth(status=HealthStatus.HEALTHY, message="ok")
        assert c.latency_ms == 0.0

    def test_with_details(self):
        from app.health import ComponentHealth, HealthStatus

        c = ComponentHealth(
            status=HealthStatus.HEALTHY, message="ok", details={"version": "1.0"}
        )
        assert c.details == {"version": "1.0"}


class TestHealthCheckService:
    def test_check_database_healthy(self):
        import sys
        from types import ModuleType
        from app.health import HealthCheckService, HealthStatus

        fake_db = ModuleType("app.database")
        fake_db.get_db = MagicMock()
        fake_db_ctx = MagicMock()
        fake_db_ctx.__enter__ = MagicMock(return_value=MagicMock(execute=MagicMock()))
        fake_db_ctx.__exit__ = MagicMock(return_value=False)
        fake_db.get_db.return_value = fake_db_ctx
        sys.modules.setdefault("app.database", fake_db)

        svc = HealthCheckService()
        result = svc.check_database()
        assert result.status == HealthStatus.HEALTHY
        assert "connected" in result.message.lower()

    def test_check_database_unhealthy(self):
        import sys
        from types import ModuleType
        from app.health import HealthCheckService, HealthStatus

        fake_db = ModuleType("app.database")
        fake_db.get_db = MagicMock(side_effect=RuntimeError("db down"))
        original = sys.modules.get("app.database")
        sys.modules["app.database"] = fake_db
        try:
            svc = HealthCheckService()
            result = svc.check_database()
        finally:
            if original is not None:
                sys.modules["app.database"] = original
            else:
                sys.modules.pop("app.database", None)
        assert result.status == HealthStatus.UNHEALTHY
        assert "db down" in result.message

    def test_check_redis_degraded_when_not_configured(self):
        from app.health import HealthCheckService, HealthStatus

        svc = HealthCheckService()
        mock_app = MagicMock()
        mock_app.state.redis = None
        svc.app = mock_app
        result = svc.check_redis()
        assert result.status == HealthStatus.DEGRADED

    def test_check_redis_healthy(self):
        from app.health import HealthCheckService, HealthStatus

        svc = HealthCheckService()
        mock_app = MagicMock()
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_app.state.redis = mock_redis
        svc.app = mock_app
        result = svc.check_redis()
        assert result.status == HealthStatus.HEALTHY

    def test_check_llm_providers_healthy_when_key_set(self):
        from app.health import HealthCheckService

        svc = HealthCheckService()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            result = svc.check_llm_providers()
        assert result["openai"].status.value == "healthy"

    def test_check_llm_providers_degraded_when_key_missing(self):
        from app.health import HealthCheckService

        svc = HealthCheckService()
        with patch.dict("os.environ", {}, clear=True):
            result = svc.check_llm_providers()
        assert result["openai"].status.value == "degraded"

    def test_get_overall_health_unhealthy_when_db_down(self):
        from app.health import HealthCheckService, HealthStatus, ComponentHealth

        svc = HealthCheckService()
        unhealthy = ComponentHealth(status=HealthStatus.UNHEALTHY, message="db down")
        healthy = ComponentHealth(status=HealthStatus.HEALTHY, message="ok")
        with patch.object(svc, "check_database", return_value=unhealthy):
            with patch.object(svc, "check_redis", return_value=healthy):
                with patch.object(svc, "check_llm_providers", return_value={}):
                    with patch.object(svc, "check_memory", return_value=healthy):
                        with patch.object(svc, "check_disk", return_value=healthy):
                            result = svc.get_overall_health()
        assert result["status"] == "unhealthy"

    def test_get_overall_health_healthy_when_all_ok(self):
        from app.health import HealthCheckService, HealthStatus, ComponentHealth

        svc = HealthCheckService()
        healthy = ComponentHealth(status=HealthStatus.HEALTHY, message="ok")
        with patch.object(svc, "check_database", return_value=healthy):
            with patch.object(svc, "check_redis", return_value=healthy):
                with patch.object(svc, "check_llm_providers", return_value={}):
                    with patch.object(svc, "check_memory", return_value=healthy):
                        with patch.object(svc, "check_disk", return_value=healthy):
                            result = svc.get_overall_health()
        assert result["status"] == "healthy"

    def test_history_capped_at_100(self):
        from app.health import HealthCheckService, HealthStatus, ComponentHealth

        svc = HealthCheckService()
        healthy = ComponentHealth(status=HealthStatus.HEALTHY, message="ok")
        with patch.object(svc, "check_database", return_value=healthy):
            with patch.object(svc, "check_redis", return_value=healthy):
                with patch.object(svc, "check_llm_providers", return_value={}):
                    with patch.object(svc, "check_memory", return_value=healthy):
                        with patch.object(svc, "check_disk", return_value=healthy):
                            for _ in range(110):
                                svc.get_overall_health()
        assert len(svc.history()) <= 100

    def test_is_healthy_true(self):
        from app.health import HealthCheckService

        svc = HealthCheckService()
        healthy = MagicMock(status=MagicMock(value="healthy"))
        with patch.object(svc, "get_overall_health", return_value={"status": "healthy"}):
            assert svc.is_healthy() is True

    def test_is_healthy_false(self):
        from app.health import HealthCheckService

        svc = HealthCheckService()
        with patch.object(svc, "get_overall_health", return_value={"status": "unhealthy"}):
            assert svc.is_healthy() is False

    def test_health_service_singleton_importable(self):
        from app.health import health_service

        assert health_service is not None
        assert hasattr(health_service, "get_overall_health")
