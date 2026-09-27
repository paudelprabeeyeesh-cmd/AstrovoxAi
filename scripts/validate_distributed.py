#!/usr/bin/env python3
"""
Phase F Distributed Validation CLI
====================================

Runs all distributed tests via pytest and produces a pass/fail/skip report
per strategy.  Output is emitted as Markdown (default) and/or JSON.

Usage examples:
    python scripts/validate_distributed.py
    python scripts/validate_distributed.py --markers gpu distributed
    python scripts/validate_distributed.py --no-markdown --output-json report.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ===========================================================================
# Report model
# ===========================================================================

class ValidationReport:
    def __init__(self) -> None:
        self.timestamp: str = datetime.now().isoformat()
        self.tests: list[dict[str, Any]] = []
        self.passed: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.errors: int = 0
        self.strategies: dict[str, dict[str, int]] = {}

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _infer_strategy(nodeid: str) -> str:
        name = nodeid.lower()
        if "ddp" in name:
            return "DDP"
        if "fsdp" in name:
            return "FSDP"
        if "zero" in name:
            return "ZeRO"
        if "tensor_parallel" in name or "tp" in name.split("/")[-1]:
            return "TensorParallel"
        if "pipeline_parallel" in name or "pp" in name.split("/")[-1]:
            return "PipelineParallel"
        if "cpu_offload" in name:
            return "CPUOffload"
        if "checkpoint" in name:
            return "Checkpoint"
        if "failure" in name or "recovery" in name:
            return "FailureRecovery"
        if "scaling" in name:
            return "ScalingEfficiency"
        if "setup" in name:
            return "Setup"
        return "Other"

    def _ensure_strategy(self, strategy: str) -> None:
        if strategy not in self.strategies:
            self.strategies[strategy] = {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0,
            }

    # -- public API -------------------------------------------------------

    def add_test(
        self,
        name: str,
        outcome: str,
        markers: list[str] | None = None,
        duration: float | None = None,
        message: str | None = None,
    ) -> None:
        self.tests.append(
            {
                "name": name,
                "outcome": outcome,
                "markers": markers or [],
                "duration": duration,
                "message": message,
            }
        )
        counter = {
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
        }.get(outcome)
        if counter is not None:
            if outcome == "passed":
                self.passed += 1
            elif outcome == "failed":
                self.failed += 1
            elif outcome == "skipped":
                self.skipped += 1
        else:
            self.errors += 1

        strategy = self._infer_strategy(name)
        self._ensure_strategy(strategy)
        bucket = outcome if outcome in ("passed", "failed", "skipped") else "errors"
        self.strategies[strategy][bucket] += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "errors": self.errors,
                "total": len(self.tests),
            },
            "strategies": self.strategies,
            "tests": self.tests,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Distributed Validation Report",
            "",
            f"Generated: {self.timestamp}",
            "",
            "## Summary",
            "",
            "| Status | Count |",
            "|--------|------:|",
            f"| Passed | {self.passed} |",
            f"| Failed | {self.failed} |",
            f"| Skipped | {self.skipped} |",
            f"| Errors | {self.errors} |",
            f"| Total  | {len(self.tests)} |",
            "",
            "## Strategies",
            "",
            "| Strategy | Passed | Failed | Skipped | Errors |",
            "|----------|------:|------:|--------:|-------:|",
        ]
        for strategy in sorted(self.strategies):
            counts = self.strategies[strategy]
            lines.append(
                f"| {strategy} "
                f"| {counts['passed']} "
                f"| {counts['failed']} "
                f"| {counts['skipped']} "
                f"| {counts['errors']} |"
            )

        lines.extend(
            [
                "",
                "## Tests",
                "",
                "| Test | Status | Strategy |",
                "|------|--------|----------|",
            ]
        )
        for test in self.tests:
            strategy = self._infer_strategy(test["name"])
            lines.append(f"| {test['name']} | {test['outcome']} | {strategy} |")

        return "\n".join(lines)


# ===========================================================================
# Pytest plugin
# ===========================================================================

class ResultCollector:
    """Pytest plugin that records per-test outcomes into a ValidationReport."""

    def __init__(self, report: ValidationReport) -> None:
        self.report = report

    def pytest_runtest_logreport(self, report: Any) -> None:
        # Only record the actual test call, not setup/teardown
        if report.when != "call":
            return

        markers = sorted(report.keywords)
        duration = getattr(report, "duration", None)
        message = None
        if report.failed:
            longrepr = getattr(report, "longrepr", None)
            if longrepr is not None:
                message = str(longrepr)

        self.report.add_test(
            name=report.nodeid,
            outcome=report.outcome,
            markers=markers,
            duration=duration,
            message=message,
        )


# ===========================================================================
# Runner
# ===========================================================================

def run_validation(
    test_path: str,
    markers: list[str] | None = None,
    output_json: str | None = None,
    output_markdown: str | None = None,
) -> int:
    import pytest

    report = ValidationReport()
    collector = ResultCollector(report)

    args = [test_path, "-v", "-rA", "--tb=short"]
    if markers:
        for marker in markers:
            args.extend(["-m", marker])

    exit_code = pytest.main(args, plugins=[collector])

    # Write reports
    if output_json:
        with open(output_json, "w", encoding="utf-8") as fh:
            json.dump(report.to_dict(), fh, indent=2)
        print(f"JSON report written to: {output_json}")

    if output_markdown:
        with open(output_markdown, "w", encoding="utf-8") as fh:
            fh.write(report.to_markdown())
        print(f"Markdown report written to: {output_markdown}")

    # Print summary to stdout
    print("\n" + report.to_markdown())

    return int(exit_code)


# ===========================================================================
# CLI
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase F Distributed Validation CLI",
    )
    parser.add_argument(
        "--test-path",
        default="tests/test_distributed.py",
        help="Path to the distributed test module",
    )
    parser.add_argument(
        "--markers",
        nargs="*",
        default=None,
        help="Optional pytest markers to filter by (e.g. gpu distributed)",
    )
    parser.add_argument(
        "--output-json",
        default="validation_report.json",
        help="Path for the JSON report",
    )
    parser.add_argument(
        "--output-markdown",
        default="validation_report.md",
        help="Path for the Markdown report",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Skip Markdown report generation",
    )

    args = parser.parse_args()

    start = time.time()
    exit_code = run_validation(
        test_path=args.test_path,
        markers=args.markers,
        output_json=args.output_json,
        output_markdown=None if args.no_markdown else args.output_markdown,
    )
    elapsed = time.time() - start

    print(f"\nValidation completed in {elapsed:.2f}s")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
