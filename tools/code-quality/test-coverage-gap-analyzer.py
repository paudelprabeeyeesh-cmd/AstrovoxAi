#!/usr/bin/env python3
"""
Test Coverage Gap Analyzer - Identifies untested code paths.
"""
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


def find_test_files(base: Path) -> set[str]:
    tests = set()
    for test_file in base.rglob("test_*.py"):
        module = test_file.stem.replace("test_", "")
        tests.add(module)
    for test_file in base.rglob("*_test.py"):
        module = test_file.stem.replace("_test", "")
        tests.add(module)
    return tests


def find_source_modules(base: Path) -> list[str]:
    modules = []
    for py_file in sorted(base.rglob("*.py")):
        if py_file.name.startswith("test_") or py_file.name.startswith("__"):
            continue
        modules.append(py_file.stem)
    return modules


def analyze_coverage_gaps(src: Path, tests: Path) -> dict[str, Any]:
    tested = find_test_files(tests)
    source_modules = find_source_modules(src)
    untested = [m for m in source_modules if m not in tested]
    return {"total_modules": len(source_modules), "tested_modules": len(source_modules) - len(untested), "untested_modules": sorted(untested)[:50]}


if __name__ == "__main__":
    src = Path("02-Backend/app")
    tests = Path("02-Backend/tests")
    if not src.exists():
        src = Path(".")
        tests = Path("tests")
    report = analyze_coverage_gaps(src, tests)
    Path("code-quality-reports/coverage-gap-report.json").write_text(json.dumps(report, indent=2))
    print(f"Test coverage: {report['tested_modules']}/{report['total_modules']} modules")
    if report["untested_modules"]:
        print(f"Found {len(report['untested_modules'])} untested modules")
        sys.exit(1)
    print("All modules have tests")
    sys.exit(0)
