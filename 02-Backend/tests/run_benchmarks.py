#!/usr/bin/env python3
"""CLI entry point for benchmark evaluation."""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tests.benchmark import BenchmarkRunner


def main():
    runner = BenchmarkRunner()
    results = runner.run_all(sample_size=10)
    report = [r.to_dict() for r in results.values()]
    output = {
        "timestamp": time.time(),
        "benchmarks": report,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
