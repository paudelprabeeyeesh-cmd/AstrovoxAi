"""Load testing suite with real concurrency scenarios."""
import asyncio
import time
import statistics
from dataclasses import dataclass, field
from typing import Any

import aiohttp


@dataclass
class LoadTestResult:
    scenario: str
    concurrency: int
    duration_seconds: float
    total_requests: int
    success_requests: int
    failed_requests: int
    latencies_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.success_requests / max(self.total_requests, 1)

    @property
    def error_rate(self) -> float:
        return self.failed_requests / max(self.total_requests, 1)

    @property
    def avg_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    @property
    def p99_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def summary(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "concurrency": self.concurrency,
            "duration_seconds": round(self.duration_seconds, 2),
            "total_requests": self.total_requests,
            "success_requests": self.success_requests,
            "failed_requests": self.failed_requests,
            "success_rate_pct": round(self.success_rate * 100, 2),
            "error_rate_pct": round(self.error_rate * 100, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "error_samples": self.errors[:10],
        }


class LoadTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self.scenarios: dict[str, dict[str, Any]] = {}

    def add_scenario(self, name: str, path: str, method: str = "GET", payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> None:
        self.scenarios[name] = {
            "path": path,
            "method": method.upper(),
            "payload": payload,
            "headers": headers or {},
        }

    async def _request(self, session: aiohttp.ClientSession, scenario_name: str) -> tuple[bool, float, str | None]:
        config = self.scenarios[scenario_name]
        url = f"{self.base_url}{config['path']}"
        method = config["method"]
        payload = config.get("payload")
        headers = config.get("headers", {})
        start = time.perf_counter()
        error: str | None = None
        success = False
        try:
            async with session.request(method, url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                await resp.text()
                success = 200 <= resp.status < 400
                if not success:
                    error = f"HTTP {resp.status}"
        except Exception as exc:  # pragma: no cover - network failures in tests
            error = str(exc)
        latency_ms = (time.perf_counter() - start) * 1000
        return success, latency_ms, error

    async def run(self, name: str, concurrency: int, duration_seconds: float) -> LoadTestResult:
        if name not in self.scenarios:
            raise ValueError(f"Scenario {name} not found")
        result = LoadTestResult(scenario=name, concurrency=concurrency, duration_seconds=0.0, total_requests=0, success_requests=0, failed_requests=0)
        start = time.perf_counter()
        async with aiohttp.ClientSession() as session:
            end_time = start + duration_seconds
            tasks: list[asyncio.Task] = []
            while time.perf_counter() < end_time:
                if len(tasks) < concurrency:
                    tasks.append(asyncio.create_task(self._request(session, name)))
                else:
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        success, latency_ms, error = task.result()
                        result.total_requests += 1
                        result.latencies_ms.append(latency_ms)
                        if success:
                            result.success_requests += 1
                        else:
                            result.failed_requests += 1
                            if error:
                                result.errors.append(error)
                    tasks = list(pending)
            for task in tasks:
                task.cancel()
        result.duration_seconds = time.perf_counter() - start
        return result

    async def run_suite(self, name: str, concurrency_levels: list[int], duration_seconds: float = 30.0) -> dict[str, Any]:
        results = []
        for concurrency in concurrency_levels:
            result = await self.run(name, concurrency, duration_seconds)
            results.append(result)
        return {
            "scenario": name,
            "results": [result.summary() for result in results],
        }
