#!/usr/bin/env python3
"""Run Black formatter, Ruff linter, and generate formatting report."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPORT_PATH = Path("format_report.json")


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def run_black() -> dict[str, Any]:
    report: dict[str, Any] = {"tool": "black", "command": ["black", "--check", "--diff", "."], "returncode": 0, "stdout": "", "stderr": "", "fixed": False}
    code, stdout, stderr = _run(["black", "--check", "--diff", "."])
    report["returncode"] = code
    report["stdout"] = stdout
    report["stderr"] = stderr

    if code != 0:
        fix_code, fix_stdout, _ = _run(["black", "."])
        report["fixed"] = fix_code == 0
        report["fix_stdout"] = fix_stdout

    return report


def run_ruff() -> dict[str, Any]:
    report: dict[str, Any] = {"tool": "ruff", "command": ["ruff", "check", "."], "returncode": 0, "stdout": "", "stderr": "", "fixed": False}
    code, stdout, stderr = _run(["ruff", "check", "."])
    report["returncode"] = code
    report["stdout"] = stdout
    report["stderr"] = stderr

    if code != 0:
        fix_code, fix_stdout, fix_stderr = _run(["ruff", "check", "--fix", "."])
        report["fixed"] = fix_code == 0
        report["fix_stdout"] = fix_stdout
        report["fix_stderr"] = fix_stderr

    return report


def main() -> int:
    report_data: dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "tools": [],
    }

    tools = [run_black(), run_ruff()]
    report_data["tools"] = tools

    failed = [t for t in tools if t["returncode"] != 0 and not t.get("fixed")]

    print("=" * 60)
    print("Formatting Report")
    print("=" * 60)
    for tool in tools:
        status = "OK" if tool["returncode"] == 0 else ("FIXED" if tool.get("fixed") else "FAILED")
        print(f"{tool['tool']}: {status}")
        if tool.get("stdout"):
            print(tool["stdout"])
        if tool.get("stderr"):
            print(tool["stderr"])

    if failed:
        print(f"\n{len(failed)} tool(s) still failing after auto-fix.")

    REPORT_PATH.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"\nReport saved to {REPORT_PATH}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
