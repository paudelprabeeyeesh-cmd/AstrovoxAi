
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.load_test import LoadTestSuite, LoadTestResult


class TestLoadStressTests:
    @pytest.mark.asyncio
    async def test_load_test_suite_add_scenario(self):
        suite = LoadTestSuite(base_url="http://localhost:8000")
        suite.add_scenario("health", "/health", "GET")
        assert "health" in suite.scenarios

    @pytest.mark.asyncio
    async def test_load_test_suite_run_scenario(self):
        suite = LoadTestSuite(base_url="http://localhost:8000")
        suite.add_scenario("health", "/health", "GET")
        with patch("app.load_test.aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value="ok")
            mock_session.request.return_value.__aenter__.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            result = await suite.run("health", concurrency=1, duration_seconds=0.1)
            assert isinstance(result, LoadTestResult)
            assert result.total_requests >= 0

    def test_load_test_result_properties(self):
        result = LoadTestResult(scenario="test", concurrency=1, duration_seconds=1.0, total_requests=10, success_requests=8, failed_requests=2)
        assert result.success_rate == 0.8
        assert result.error_rate == 0.2
        assert result.avg_latency_ms == 0.0
        assert result.p95_latency_ms == 0.0
        assert result.p99_latency_ms == 0.0

    def test_load_test_result_summary(self):
        result = LoadTestResult(scenario="test", concurrency=1, duration_seconds=1.0, total_requests=10, success_requests=8, failed_requests=2)
        summary = result.summary()
        assert summary["scenario"] == "test"
        assert summary["success_rate_pct"] == 80.0
        assert summary["error_rate_pct"] == 20.0

    @pytest.mark.asyncio
    async def test_load_test_suite_run_suite(self):
        suite = LoadTestSuite(base_url="http://localhost:8000")
        suite.add_scenario("health", "/health", "GET")
        with patch("app.load_test.aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value="ok")
            mock_session.request.return_value.__aenter__.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            suite_result = await suite.run_suite("health", concurrency_levels=[1], duration_seconds=0.1)
            assert "scenario" in suite_result
            assert "results" in suite_result
