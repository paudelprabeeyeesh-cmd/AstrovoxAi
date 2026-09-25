#!/usr/bin/env python3
"""
Security Lint Rules - Detects common security anti-patterns in code.
"""
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36,}"),
    re.compile(r"xox[baprs]-[a-zA-Z0-9-]+"),
    re.compile(r"(password|passwd|pwd|secret|token|api_key)\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
]

UNSAFE_PATTERNS = [
    re.compile(r"eval\("),
    re.compile(r"exec\("),
    re.compile(r"__import__\("),
    re.compile(r"pickle\.loads\("),
    re.compile(r"yaml\.load\("),
    re.compile(r"os\.system\("),
    re.compile(r"subprocess\.call\(.*shell\s*=\s*True"),
    re.compile(r"requests\.get\(.*verify\s*=\s*False"),
]


def scan_file(path: Path) -> list[dict[str, Any]]:
    issues = []
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return []
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        for pat in SECRET_PATTERNS:
            if pat.search(line):
                issues.append({"file": str(path), "line": lineno, "rule": "hardcoded_secret", "severity": "critical"})
                break
        for pat in UNSAFE_PATTERNS:
            if pat.search(line):
                issues.append({"file": str(path), "line": lineno, "rule": "unsafe_pattern", "severity": "high"})
                break
    return issues


def scan_directory(base: Path) -> list[dict[str, Any]]:
    issues = []
    for ext in ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx"]:
        for path in sorted(base.rglob(ext)):
            if "node_modules" in str(path) or "dist" in str(path):
                continue
            issues.extend(scan_file(path))
    return issues


if __name__ == "__main__":
    target = Path(".") if Path("02-Backend/app").exists() else Path(".")
    issues = scan_directory(target)
    Path("code-quality-reports/security-lint-report.json").write_text(json.dumps(issues, indent=2))
    if issues:
        print(f"Found {len(issues)} security lint issues")
        sys.exit(1)
    print("No security lint issues found")
    sys.exit(0)
