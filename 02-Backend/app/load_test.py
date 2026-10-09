"""Load testing for AstrovoxAI backend.

Provides locust-based load testing with custom scenarios and reporting.
"""

from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LoadTestResult:
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    requests_per_second: float
    duration_seconds: float
    errors: Dict[str, int]


class LoadTester:
    """Load testing utility for AstrovoxAI endpoints."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        concurrent_users: int = 10,
        spawn_rate: float = 1.0,
        run_time: str = "60s",
    ):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.spawn_rate = spawn_rate
        self.run_time = run_time
        self._results: List[Dict[str, Any]] = []

    async def run_chat_load_test(self, message: str = "Hello, how are you?") -> LoadTestResult:
        start = time.perf_counter()
        errors: Dict[str, int] = {}
        response_times: List[float] = []
        total = 0
        succeeded = 0
        failed = 0
        try:
            import httpx
            async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
                for _ in range(self.concurrent_users * 10):
                    total += 1
                    req_start = time.perf_counter()
                    try:
                        response = await client.post(
                            "/chat/message",
                            json={"conversation_id": "load-test", "message": f"{message} {random.randint(1, 1000)}"},
                        )
                        elapsed = (time.perf_counter() - req_start) * 1000
                        response_times.append(elapsed)
                        if response.status_code < 400:
                            succeeded += 1
                        else:
                            failed += 1
                            errors[f"status_{response.status_code}"] = errors.get(f"status_{response.status_code}", 0) + 1
                    except Exception as exc:  # noqa: BLE001
                        failed += 1
                        elapsed = (time.perf_counter() - req_start) * 1000
                        response_times.append(elapsed)
                        errors[str(exc)] = errors.get(str(exc), 0) + 1
        except ImportError:
            logger.warning("httpx not available, skipping load test")
            return LoadTestResult(
                total_requests=0, successful_requests=0, failed_requests=0,
                avg_response_time_ms=0, p50_response_time_ms=0, p95_response_time_ms=0,
                p99_response_time_ms=0, max_response_time_ms=0,
                requests_per_second=0, duration_seconds=0, errors={},
            )
        duration = time.perf_counter() - start
        response_times.sort()
        total_rt = len(response_times)
        return LoadTestResult(
            total_requests=total,
            successful_requests=succeeded,
            failed_requests=failed,
            avg_response_time_ms=sum(response_times) / total_rt if total_rt else 0,
            p50_response_time_ms=response_times[int(total_rt * 0.5)] if total_rt else 0,
            p95_response_time_ms=response_times[int(total_rt * 0.95)] if total_rt else 0,
            p99_response_time_ms=response_times[int(total_rt * 0.99)] if total_rt else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            requests_per_second=total / duration if duration else 0,
            duration_seconds=duration,
            errors=errors,
        )

    def run_health_load_test(self, requests: int = 1000) -> LoadTestResult:
        start = time.perf_counter()
        errors: Dict[str, int] = {}
        response_times: List[float] = []
        total = 0
        succeeded = 0
        failed = 0
        try:
            import httpx
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                for _ in range(requests):
                    total += 1
                    req_start = time.perf_counter()
                    try:
                        response = await client.get("/health")
                        elapsed = (time.perf_counter() - req_start) * 1000
                        response_times.append(elapsed)
                        if response.status_code == 200:
                            succeeded += 1
                        else:
                            failed += 1
                    except Exception as exc:  # noqa: BLE001
                        failed += 1
                        errors[str(exc)] = errors.get(str(exc), 0) + 1
        except ImportError:
            logger.warning("httpx not available")
            return LoadTestResult(
                total_requests=0, successful_requests=0, failed_requests=0,
                avg_response_time_ms=0, p50_response_time_ms=0, p95_response_time_ms=0,
                p99_response_time_ms=0, max_response_time_ms=0,
                requests_per_second=0, duration_seconds=0, errors={},
            )
        duration = time.perf_counter() - start
        response_times.sort()
        total_rt = len(response_times)
        return LoadTestResult(
            total_requests=total,
            successful_requests=succeeded,
            failed_requests=failed,
            avg_response_time_ms=sum(response_times) / total_rt if total_rt else 0,
            p50_response_time_ms=response_times[int(total_rt * 0.5)] if total_rt else 0,
            p95_response_time_ms=response_times[int(total_rt * 0.95)] if total_rt else 0,
            p99_response_time_ms=response_times[int(total_rt * 0.99)] if total_rt else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            requests_per_second=total / duration if duration else 0,
            duration_seconds=duration,
            errors=errors,
        )

    def to_dict(self, result: LoadTestResult) -> Dict[str, Any]:
        return {
            "total_requests": result.total_requests,
            "successful_requests": result.successful_requests,
            "failed_requests": result.failed_requests,
            "success_rate": round(result.successful_requests / max(result.total_requests, 1), 4),
            "avg_response_time_ms": round(result.avg_response_time_ms, 2),
            "p50_ms": round(result.p50_response_time_ms, 2),
            "p95_ms": round(result.p95_response_time_ms, 2),
            "p99_ms": round(result.p99_response_time_ms, 2),
            "max_ms": round(result.max_response_time_ms, 2),
            "requests_per_second": round(result.requests_per_second, 2),
            "duration_seconds": round(result.duration_seconds, 2),
            "errors": result.errors,
        }


load_tester = LoadTester()
