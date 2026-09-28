#!/usr/bin/env python3
"""Run unit and integration tests, generate coverage and test reports."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPORT_DIR = Path("test-reports")
UNIT_REPORT = REPORT_DIR / "unit-test-report.json"
INTEGRATION_REPORT = REPORT_DIR / "integration-test-report.json"
COVERAGE_REPORT = REPORT_DIR / "coverage-report.json"


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def run_unit_tests() -> dict[str, Any]:
    report: dict[str, Any] = {
        "name": "unit",
        "command": ["pytest", "tests/", "-v", "--tb=short", "-k", "not integration"],
        "returncode": 0,
        "stdout": "",
        "stderr": "",
    }
    cmd = [
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "-k",
        "not integration",
        "--cov=models",
        "--cov=model",
        "--cov=backend",
        "--cov=ASTROVOX_AI",
        "--cov-report=term-missing",
        "--cov-report=json:" + str(COVERAGE_REPORT),
    ]
    code, stdout, stderr = _run(cmd)
    report["returncode"] = code
    report["stdout"] = stdout
    report["stderr"] = stderr
    return report


def run_integration_tests() -> dict[str, Any]:
    report: dict[str, Any] = {
        "name": "integration",
        "command": ["pytest", "tests/", "-v", "--tb=short", "-m", "integration"],
        "returncode": 0,
        "stdout": "",
        "stderr": "",
    }
    code, stdout, stderr = _run(report["command"])
    report["returncode"] = code
    report["stdout"] = stdout
    report["stderr"] = stderr
    return report


def main() -> int:
    REPORT_DIR.mkdir(exist_ok=True)

    unit = run_unit_tests()
    integration = run_integration_tests()

    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "unit": {
            "returncode": unit["returncode"],
            "stdout": unit["stdout"],
            "stderr": unit["stderr"],
        },
        "integration": {
            "returncode": integration["returncode"],
            "stdout": integration["stdout"],
            "stderr": integration["stderr"],
        },
    }

    print("=" * 60)
    print("Test Report")
    print("=" * 60)
    for label, data in [("Unit", unit), ("Integration", integration)]:
        status = "PASSED" if data["returncode"] == 0 else "FAILED"
        print(f"{label}: {status}")
        if data.get("stdout"):
            print(data["stdout"])
        if data.get("stderr"):
            print(data["stderr"])

    if unit["returncode"] != 0 or integration["returncode"] != 0:
        summary["result"] = "FAILED"
    else:
        summary["result"] = "PASSED"

    (REPORT_DIR / "test-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nReports saved to {REPORT_DIR}/")

    return 1 if summary["result"] == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
