#!/usr/bin/env python3
"""
Performance Regression Detector - Identifies potential performance bottlenecks.
"""
import ast
import json
import sys
from pathlib import Path
from typing import Any


BOTTLENECK_PATTERNS = [
    (re.compile(r"for .+ in .+:\s*\n.*for .+ in"), "nested_loop"),
    (re.compile(r"\.append\(.*\)"), "list_append_in_loop"),
    (re.compile(r"\+.*for .+ in"), "string_concat_in_loop"),
    (re.compile(r"time\.sleep\("), "blocking_sleep"),
    (re.compile(r"requests\.get\("), "sync_http_call"),
    (re.compile(r"SELECT \* FROM"), "select_star"),
]


def scan_file(path: Path) -> list[dict[str, Any]]:
    issues = []
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return []
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        for pat, rule in BOTTLENECK_PATTERNS:
            if pat.search(line):
                issues.append({"file": str(path), "line": lineno, "rule": rule, "severity": "medium"})
    return issues


def scan_directory(base: Path) -> list[dict[str, Any]]:
    issues = []
    for ext in ["*.py", "*.ts", "*.tsx"]:
        for path in sorted(base.rglob(ext)):
            if "node_modules" in str(path) or "dist" in str(path) or "test" in str(path).lower():
                continue
            issues.extend(scan_file(path))
    return issues[:100]


if __name__ == "__main__":
    target = Path(".") if Path("02-Backend/app").exists() else Path(".")
    issues = scan_directory(target)
    Path("code-quality-reports/performance-regression-report.json").write_text(json.dumps(issues, indent=2))
    if issues:
        print(f"Found {len(issues)} potential performance issues")
        sys.exit(1)
    print("No obvious performance regressions found")
    sys.exit(0)
