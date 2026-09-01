"""Scalability Engineering — horizontal/vertical scaling, caching, optimization."""

import time
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScalingPolicy:
    """Auto-scaling policy."""
    min_instances: int = 1
    max_instances: int = 10
    target_cpu_percent: float = 70.0
    target_memory_percent: float = 80.0
    scale_up_cooldown: int = 60
    scale_down_cooldown: int = 300


class AutoScaler:
    """Auto-scaling manager."""

    def __init__(self, policy: ScalingPolicy = None):
        self._policy = policy or ScalingPolicy()
        self._current_instances = 1
        self._last_scale_time = 0

    def evaluate(self, cpu_percent: float, memory_percent: float) -> str:
        """Evaluate if scaling is needed."""
        now = time.time()

        if cpu_percent > self._policy.target_cpu_percent or memory_percent > self._policy.target_memory_percent:
            if self._current_instances < self._policy.max_instances:
                if now - self._last_scale_time > self._policy.scale_up_cooldown:
                    self._current_instances += 1
                    self._last_scale_time = now
                    return "scale_up"

        if cpu_percent < self._policy.target_cpu_percent * 0.5 and memory_percent < self._policy.target_memory_percent * 0.5:
            if self._current_instances > self._policy.min_instances:
                if now - self._last_scale_time > self._policy.scale_down_cooldown:
                    self._current_instances -= 1
                    self._last_scale_time = now
                    return "scale_down"

        return "no_action"

    def get_status(self) -> dict:
        """Get current scaling status."""
        return {
            "current_instances": self._current_instances,
            "min_instances": self._policy.min_instances,
            "max_instances": self._policy.max_instances,
        }


class CacheStrategy:
    """Cache strategy manager."""

    def __init__(self):
        self._strategies: dict = {}

    def set_strategy(self, key_pattern: str, ttl: int, max_size: int = 1000):
        """Set cache strategy for a key pattern."""
        self._strategies[key_pattern] = {
            "ttl": ttl,
            "max_size": max_size,
        }

    def get_ttl(self, key: str) -> int:
        """Get TTL for a key."""
        for pattern, config in self._strategies.items():
            if pattern in key:
                return config["ttl"]
        return 300


class LoadTestRunner:
    """Run load tests."""

    def __init__(self):
        self._results: list = []

    async def run_load_test(self, url: str, concurrency: int, duration: int) -> dict:
        """Run a load test."""
        import httpx
        import asyncio

        results = {"total": 0, "success": 0, "failed": 0, "times": []}

        async def make_request():
            start = time.time()
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=10)
                    elapsed = time.time() - start
                    results["total"] += 1
                    results["times"].append(elapsed)
                    if resp.status_code == 200:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
            except Exception:
                results["total"] += 1
                results["failed"] += 1

        start_time = time.time()
        tasks = []
        while time.time() - start_time < duration:
            for _ in range(concurrency):
                tasks.append(asyncio.create_task(make_request()))
            await asyncio.sleep(0.1)

        await asyncio.gather(*tasks, return_exceptions=True)

        if results["times"]:
            results["avg_time_ms"] = sum(results["times"]) / len(results["times"]) * 1000
            results["p95_time_ms"] = sorted(results["times"])[int(len(results["times"]) * 0.95)] * 1000

        self._results.append(results)
        return results


import asyncio

auto_scaler = AutoScaler()
cache_strategy = CacheStrategy()
load_test_runner = LoadTestRunner()
