# Load testing script for AstrovoxAI
# Usage: python scripts/load_test.py
# Requires: pip install locust

import os
import sys
import json
import time
import random
import statistics
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-Backend"))

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


class LoadTester:
    """Simple load tester for AstrovoxAI API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []

    def test_health_endpoint(self, iterations: int = 100):
        """Test health endpoint under load."""
        print(f"Testing /health endpoint ({iterations} requests)...")
        times = []
        errors = 0

        with httpx.Client() as client:
            for i in range(iterations):
                start = time.time()
                try:
                    resp = client.get(f"{self.base_url}/health", timeout=5)
                    elapsed = time.time() - start
                    times.append(elapsed)
                    if resp.status_code != 200:
                        errors += 1
                except Exception:
                    errors += 1

        self._report("health", times, errors, iterations)

    def test_models_endpoint(self, iterations: int = 50):
        """Test models endpoint."""
        print(f"Testing /chat/models endpoint ({iterations} requests)...")
        times = []
        errors = 0

        with httpx.Client() as client:
            for i in range(iterations):
                start = time.time()
                try:
                    resp = client.get(f"{self.base_url}/chat/models", timeout=5)
                    elapsed = time.time() - start
                    times.append(elapsed)
                    if resp.status_code != 200:
                        errors += 1
                except Exception:
                    errors += 1

        self._report("models", times, errors, iterations)

    def test_concurrent_requests(self, concurrency: int = 10, total: int = 100):
        """Test concurrent request handling."""
        print(f"Testing concurrent requests ({concurrency} concurrent, {total} total)...")
        import concurrent.futures

        times = []
        errors = 0

        def make_request():
            start = time.time()
            try:
                with httpx.Client() as client:
                    resp = client.get(f"{self.base_url}/health", timeout=10)
                    elapsed = time.time() - start
                    return elapsed, resp.status_code == 200
            except Exception:
                return time.time() - start, False

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(make_request) for _ in range(total)]
            for future in concurrent.futures.as_completed(futures):
                elapsed, success = future.result()
                times.append(elapsed)
                if not success:
                    errors += 1

        self._report("concurrent", times, errors, total)

    def _report(self, name: str, times: list, errors: int, total: int):
        """Print test report."""
        if not times:
            print(f"  {name}: No successful requests")
            return

        print(f"  {name}:")
        print(f"    Total: {total}, Errors: {errors} ({errors/total*100:.1f}%)")
        print(f"    Avg: {statistics.mean(times)*1000:.1f}ms")
        print(f"    Min: {min(times)*1000:.1f}ms")
        print(f"    Max: {max(times)*1000:.1f}ms")
        if len(times) > 1:
            print(f"    P50: {statistics.median(times)*1000:.1f}ms")
            sorted_times = sorted(times)
            p95_idx = int(len(sorted_times) * 0.95)
            print(f"    P95: {sorted_times[p95_idx]*1000:.1f}ms")
        print()

        self.results.append({
            "test": name,
            "total": total,
            "errors": errors,
            "avg_ms": statistics.mean(times) * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
        })

    def generate_report(self) -> dict:
        """Generate full test report."""
        return {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "tests": self.results,
            "summary": {
                "total_tests": len(self.results),
                "total_requests": sum(r["total"] for r in self.results),
                "total_errors": sum(r["errors"] for r in self.results),
            },
        }


def main():
    """Run load tests."""
    import argparse

    parser = argparse.ArgumentParser(description="AstrovoxAI Load Tester")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--iterations", type=int, default=100, help="Iterations per test")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent requests")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    tester = LoadTester(args.url)

    print("=" * 60)
    print("AstrovoxAI Load Test")
    print("=" * 60)
    print()

    tester.test_health_endpoint(args.iterations)
    tester.test_models_endpoint(args.iterations // 2)
    tester.test_concurrent_requests(args.concurrency, args.iterations)

    report = tester.generate_report()

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total requests: {report['summary']['total_requests']}")
    print(f"Total errors: {report['summary']['total_errors']}")
    error_rate = report['summary']['total_errors'] / max(report['summary']['total_requests'], 1)
    print(f"Error rate: {error_rate*100:.2f}%")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()
