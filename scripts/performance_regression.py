"""Performance regression tracker for CI.

Compares current benchmark results against a baseline and fails when a
regression exceeds the configured threshold. Results are stored as JSON
artifacts so they can be used as baselines for later runs.

Usage:
    python scripts/performance_regression.py \
        --baseline benchmark_baseline.json \
        --current benchmark_results.json \
        --threshold 0.10 \
        --fail-on-regression
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RegressionConfig:
    baseline_path: Path
    current_path: Path
    threshold: float
    fail_on_regression: bool


def _load_cases(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("cases", [])
    return {case["name"]: case for case in cases}


def _check_regression(config: RegressionConfig) -> tuple[list[str], list[str]]:
    baseline = _load_cases(config.baseline_path)
    current = _load_cases(config.current_path)
    regressions: list[str] = []
    passes: list[str] = []
    for name, case in current.items():
        if name not in baseline:
            continue
        base_ms = float(baseline[name].get("astrovox_ms", 0) or 0)
        current_ms = float(case.get("astrovox_ms", 0) or 0)
        if base_ms <= 0 or current_ms <= 0:
            continue
        slowdown = (current_ms - base_ms) / base_ms
        if slowdown > config.threshold:
            regressions.append(
                f"{name}: baseline {base_ms:.3f}ms -> current {current_ms:.3f}ms "
                f"({slowdown*100:.1f}% slower)"
            )
        else:
            passes.append(f"{name}: within threshold ({slowdown*100:.1f}%)")
    return regressions, passes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Performance regression checker")
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--threshold", default=0.10, type=float,
                        help="Regression threshold as a fraction, e.g. 0.10 = 10%%")
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args(argv)
    config = RegressionConfig(
        baseline_path=args.baseline,
        current_path=args.current,
        threshold=args.threshold,
        fail_on_regression=args.fail_on_regression,
    )
    regressions, passes = _check_regression(config)
    for line in passes:
        print(f"[perf] PASS {line}")
    for line in regressions:
        print(f"[perf] REGRESSION {line}", file=sys.stderr)
    print(f"[perf] checked {len(passes) + len(regressions)} cases, "
          f"{len(regressions)} regressions found")
    if regressions and config.fail_on_regression:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
