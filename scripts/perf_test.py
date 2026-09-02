#!/usr/bin/env python3
"""Performance and load testing script for AstrovoxAI.

Usage:
    python scripts/perf_test.py
    python scripts/perf_test.py --url http://localhost:8000 --users 100
"""

import os
import sys
import time
import json
import statistics
import argparse
import concurrent.futures
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-Backend"))

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


class PerformanceTester:
    """Run performance tests against the API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = defaultdict(list)

    def _time_request(self, method: str, path: str, **kwargs) -> tuple[float, int, str]:
        """Time a single request. Returns (duration, status, path)."""
        start = time.perf_counter()
        try:
            with httpx.Client() as client:
                resp = getattr(client, method.lower())(
                    f"{self.base_url}{path}", timeout=10, **kwargs
                )
                elapsed = time.perf_counter() - start
                return elapsed, resp.status_code, path
        except Exception:
            elapsed = time.perf_counter() - start
            return elapsed, 0, path

    def test_health_endpoint(self, iterations: int = 100):
        """Test health endpoint performance."""
        print(f"Testing /health ({iterations} requests)...")
        for _ in range(iterations):
            duration, status, _ = self._time_request("GET", "/health")
            self.results["health"].append((duration, status))

    def test_models_endpoint(self, iterations: int = 50):
        """Test models endpoint performance."""
        print(f"Testing /chat/models ({iterations} requests)...")
        for _ in range(iterations):
            duration, status, _ = self._time_request("GET", "/chat/models")
            self.results["models"].append((duration, status))

    def test_concurrent_requests(self, concurrency: int = 50, total: int = 200):
        """Test concurrent request handling."""
        print(f"Testing concurrent requests ({concurrency} concurrent, {total} total)...")

        def make_request(_):
            return self._time_request("GET", "/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(make_request, i) for i in range(total)]
            for future in concurrent.futures.as_completed(futures):
                duration, status, _ = future.result()
                self.results["concurrent"].append((duration, status))

    def test_endpoint_latency(self):
        """Test various endpoints for latency."""
        endpoints = [
            ("GET", "/health"),
            ("GET", "/health/readiness"),
            ("GET", "/health/liveness"),
            ("GET", "/"),
            ("GET", "/chat/models"),
            ("GET", "/embeddings/status"),
        ]

        for method, path in endpoints:
            print(f"Testing {method} {path}...")
            for _ in range(20):
                duration, status, _ = self._time_request(method, path)
                key = f"{method}:{path}"
                self.results[key].append((duration, status))

    def _percentile(self, data: list[float], pct: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * pct / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def generate_report(self) -> dict:
        """Generate performance report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "tests": {}
        }

        for endpoint, measurements in self.results.items():
            if not measurements:
                continue

            durations = [m[0] * 1000 for m in measurements]
            statuses = [m[1] for m in measurements]
            success_count = sum(1 for s in statuses if 200 <= s < 400)
            error_count = len(statuses) - success_count

            report["tests"][endpoint] = {
                "requests": len(durations),
                "avg_ms": round(statistics.mean(durations), 2),
                "min_ms": round(min(durations), 2),
                "max_ms": round(max(durations), 2),
                "p50_ms": round(self._percentile(durations, 50), 2),
                "p95_ms": round(self._percentile(durations, 95), 2),
                "p99_ms": round(self._percentile(durations, 99), 2),
                "success_rate": round(success_count / len(statuses) * 100, 2),
                "error_count": error_count,
                "requests_per_second": round(
                    len(durations) / sum(durations), 2
                ) if sum(durations) > 0 else 0,
            }

        return report


def main():
    parser = argparse.ArgumentParser(description="AstrovoxAI Performance Tester")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--health-iterations", type=int, default=100)
    parser.add_argument("--models-iterations", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--total", type=int, default=200)
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    tester = PerformanceTester(args.url)

    print("=" * 60)
    print("AstrovoxAI Performance Test")
    print("=" * 60)
    print()

    tester.test_health_endpoint(args.health_iterations)
    tester.test_models_endpoint(args.models_iterations)
    tester.test_endpoint_latency()
    tester.test_concurrent_requests(args.concurrency, args.total)

    report = tester.generate_report()

    print()
    print("=" * 60)
    print("Performance Report")
    print("=" * 60)

    for endpoint, stats in report["tests"].items():
        print(f"\n{endpoint}:")
        print(f"  Requests: {stats['requests']}")
        print(f"  Avg: {stats['avg_ms']}ms")
        print(f"  P50: {stats['p50_ms']}ms")
        print(f"  P95: {stats['p95_ms']}ms")
        print(f"  P99: {stats['p99_ms']}ms")
        print(f"  Success Rate: {stats['success_rate']}%")
        print(f"  Requests/sec: {stats['requests_per_second']}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()
