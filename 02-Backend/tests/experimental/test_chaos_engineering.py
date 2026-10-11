
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.chaos_testing import ChaosRunner, RedisKillScenario, PostgresKillScenario, ChaosResult


class TestChaosEngineering:
    @pytest.mark.asyncio
    async def test_chaos_runner_registers_scenario(self):
        runner = ChaosRunner()
        mock_scenario = AsyncMock()
        runner.register("test", mock_scenario)
        assert "test" in runner.scenarios

    @pytest.mark.asyncio
    async def test_chaos_runner_runs_scenario(self):
        runner = ChaosRunner()
        mock_scenario = AsyncMock()
        mock_scenario.inject.return_value = None
        mock_scenario.recover.return_value = None
        mock_scenario.verify.return_value = True
        runner.register("test", mock_scenario)
        result = await runner.run("test", verify_after_seconds=0.1)
        assert isinstance(result, ChaosResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_chaos_runner_handles_failure(self):
        runner = ChaosRunner()
        mock_scenario = AsyncMock()
        mock_scenario.inject.side_effect = RuntimeError("injection failed")
        runner.register("fail", mock_scenario)
        result = await runner.run("fail", verify_after_seconds=0.1)
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_chaos_runner_run_all(self):
        runner = ChaosRunner()
        mock_scenario = AsyncMock()
        mock_scenario.inject.return_value = None
        mock_scenario.recover.return_value = None
        mock_scenario.verify.return_value = True
        runner.register("s1", mock_scenario)
        runner.register("s2", mock_scenario)
        results = await runner.run_all(verify_after_seconds=0.1)
        assert len(results) == 2
        assert all(r.success for r in results)
