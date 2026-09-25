"""Load testing utilities."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import aiohttp


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LoadTestConfig:
    test_id: str
    url: str
    method: str = "GET"
    concurrent_users: int = 10
    duration_seconds: int = 60
    ramp_up_seconds: int = 10
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None


@dataclass
class LoadTestResult:
    test_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    status: TestStatus = TestStatus.PENDING


class LoadTester:
    _results: Dict[str, LoadTestResult] = {}

    @classmethod
    async def run_test(cls, config: LoadTestConfig) -> LoadTestResult:
        result = LoadTestResult(test_id=config.test_id)
        result.status = TestStatus.RUNNING
        latencies = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(config.concurrent_users):
                task = cls._user_session(session, config, latencies)
                tasks.append(task)
            await asyncio.gather(*tasks)
        result.total_requests = len(latencies)
        result.successful_requests = len(latencies)
        if latencies:
            latencies.sort()
            result.avg_latency_ms = sum(latencies) / len(latencies)
            result.p95_latency_ms = latencies[int(len(latencies) * 0.95)]
            result.p99_latency_ms = latencies[int(len(latencies) * 0.99)]
        result.status = TestStatus.COMPLETED
        cls._results[config.test_id] = result
        return result

    @staticmethod
    async def _user_session(session: aiohttp.ClientSession, config: LoadTestConfig, latencies: List[float]):
        for _ in range(config.duration_seconds):
            start = datetime.now(timezone.utc)
            try:
                async with session.request(config.method, config.url, headers=config.headers, data=config.body) as resp:
                    await resp.text()
                    latencies.append((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            except Exception:
                pass
            await asyncio.sleep(1)
