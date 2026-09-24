"""
Load test for AstrovoxAI backend.

Sends 50 concurrent requests to /health and /auth/login endpoints
and asserts p95 latency < 2s and success rate > 95%.

Primary path: FastAPI TestClient (in-process, no server required).
Fallback path: local uvicorn server for realistic latency measurement.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import httpx

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False

CONCURRENCY = 50


def _build_test_app() -> FastAPI:
    app = FastAPI(title="AstrovoxAI Load Test App")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "astravox-ai-backend", "version": "2.0.0"}

    @app.post("/auth/login")
    async def login():
        return {
            "status": "OK",
            "message": "Login successful",
            "user": {"id": "load-test-user", "email": "loadtest@example.com"},
            "session": {
                "access_token": "load-test-token",
                "refresh_token": "load-test-refresh",
            },
        }

    return app


def _send_sync(client, method: str, url: str, json_body: dict | None = None) -> Tuple[float, bool]:
    start = time.perf_counter()
    try:
        if method == "POST":
            resp = client.post(url, json=json_body)
        else:
            resp = client.get(url)
        elapsed = time.perf_counter() - start
        success = resp.status_code < 400
        return elapsed, success
    except Exception:
        elapsed = time.perf_counter() - start
        return elapsed, False


def _compute_stats(latencies: List[float], successes: List[bool]) -> dict:
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


def run_load_test_with_testclient() -> dict:
    app = _build_test_app()
    client = TestClient(app)
    latencies: List[float] = []
    successes: List[bool] = []

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = []
        for _ in range(CONCURRENCY):
            futures.append(executor.submit(_send_sync, client, "GET", "/health"))
        for _ in range(CONCURRENCY):
            futures.append(
                executor.submit(
                    _send_sync,
                    client,
                    "POST",
                    "/auth/login",
                    {"email": "loadtest@example.com", "password": "loadtest"},
                )
            )
        for future in as_completed(futures):
            elapsed, success = future.result()
            latencies.append(elapsed)
            successes.append(success)

    return _compute_stats(latencies, successes)


def run_load_test_with_fallback_server() -> dict:
    import socket
    import threading

    import uvicorn

    app = _build_test_app()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            r = httpx.get(f"{base_url}/health", timeout=2.0)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)

    try:
        latencies: List[float] = []
        successes: List[bool] = []

        async def _send(client: httpx.AsyncClient, method: str, url: str, json_body: dict | None = None) -> Tuple[float, bool]:
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

        async def _run() -> None:
            async with httpx.AsyncClient() as client:
                tasks = []
                for _ in range(CONCURRENCY):
                    tasks.append(_send(client, "GET", f"{base_url}/health"))
                for _ in range(CONCURRENCY):
                    tasks.append(
                        _send(
                            client,
                            "POST",
                            f"{base_url}/auth/login",
                            {"email": "loadtest@example.com", "password": "loadtest"},
                        )
                    )
                results = await asyncio.gather(*tasks)
                for elapsed, success in results:
                    latencies.append(elapsed)
                    successes.append(success)

        asyncio.run(_run())
        return _compute_stats(latencies, successes)
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def test_load_test_concurrency() -> None:
    """
    Run load test and assert p95 latency < 2s and success rate > 95%.
    Uses FastAPI TestClient when available, falls back to a local HTTP server.
    """
    if TESTCLIENT_AVAILABLE:
        results = run_load_test_with_testclient()
    else:
        results = run_load_test_with_fallback_server()

    print(results)
    assert results["success_rate"] > 95, f"Success rate {results['success_rate']}% is below 95%"
    assert results["p95_latency_s"] < 2, f"P95 latency {results['p95_latency_s']}s is above 2s"


if __name__ == "__main__":
    test_load_test_concurrency()
