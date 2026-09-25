#!/usr/bin/env python3
"""
Code Ownership Mapping - Maps files to primary contributors using git history.
"""
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

Path("code-quality-reports").mkdir(exist_ok=True)


def get_blame(path: Path) -> dict[str, int]:
    try:
        result = subprocess.run(
            ["git", "blame", "--line-porcelain", str(path)],
            capture_output=True, text=True, timeout=30
        )
    except Exception:
        return {}
    authors: dict[str, int] = defaultdict(int)
    for line in result.stdout.splitlines():
        if line.startswith("author "):
            name = line[7:]
            authors[name] += 1
    return dict(authors)


def map_ownership(base: Path) -> dict[str, Any]:
    ownership: dict[str, dict[str, int]] = {}
    for py_file in sorted(base.rglob("*.py")):
        authors = get_blame(py_file)
        if authors:
            ownership[str(py_file)] = authors
    return ownership


if __name__ == "__main__":
    target = Path("02-Backend/app") if Path("02-Backend/app").exists() else Path(".")
    report = map_ownership(target)
    Path("code-quality-reports/code-ownership-report.json").write_text(json.dumps(report, indent=2))
    if report:
        print(f"Mapped ownership for {len(report)} files")
    sys.exit(0)
