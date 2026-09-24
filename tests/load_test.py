"""
Load test for AstrovoxAI backend.

Sends 50 concurrent requests to /health and /auth/login endpoints
and asserts p95 latency < 2s and success rate > 95%.
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Tuple

import httpx


BASE_URL = "http://localhost:8000"
CONCURRENCY = 50
HEALTH_URL = f"{BASE_URL}/health"
LOGIN_URL = f"{BASE_URL}/auth/login"


async def send_request(client: httpx.AsyncClient, url: str, method: str = "GET", json_body: dict | None = None) -> Tuple[float, bool]:
    start = time.perf_counter()
    try:
        if method == "POST":
            resp = await client.post(url, json=json_body, timeout=10.0)
        else:
            resp = await client.get(url, timeout=10.0)
        elapsed = time.perf_counter() - start
        success = resp.status_code < 400
        return elapsed, success
    except Exception:
        elapsed = time.perf_counter() - start
        return elapsed, False


async def run_load_test() -> dict:
    latencies: List[float] = []
    successes: List[bool] = []

    async with httpx.AsyncClient() as client:
        tasks = []
        for _ in range(CONCURRENCY):
            tasks.append(send_request(client, HEALTH_URL, "GET"))
        for _ in range(CONCURRENCY):
            tasks.append(send_request(client, LOGIN_URL, "POST", {"email": "loadtest@example.com", "password": "loadtest"}))

        results = await asyncio.gather(*tasks)
        for elapsed, success in results:
            latencies.append(elapsed)
            successes.append(success)

    total = len(latencies)
    success_count = sum(1 for s in successes if s)
    success_rate = success_count / total if total else 0.0

    latencies.sort()
    p95_index = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_index] if latencies else 0.0

    return {
        "total_requests": total,
        "success_count": success_count,
        "success_rate": round(success_rate * 100, 2),
        "p95_latency_s": round(p95_latency, 4),
        "avg_latency_s": round(sum(latencies) / len(latencies), 4) if latencies else 0.0,
        "min_latency_s": round(min(latencies), 4) if latencies else 0.0,
        "max_latency_s": round(max(latencies), 4) if latencies else 0.0,
    }


def test_load_test_concurrency() -> None:
    """
    Run load test and assert p95 latency < 2s and success rate > 95%.
    """
    results = asyncio.run(run_load_test())
    print(results)
    assert results["success_rate"] > 95, f"Success rate {results['success_rate']}% is below 95%"
    assert results["p95_latency_s"] < 2, f"P95 latency {results['p95_latency_s']}s is above 2s"


if __name__ == "__main__":
    test_load_test_concurrency()
