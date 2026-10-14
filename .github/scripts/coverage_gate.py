#!/usr/bin/env python3
"""Fail the build when measured coverage is below the threshold.

Called from .github/workflows/ci.yml as:

    python .github/scripts/coverage_gate.py 80 coverage-backend.xml

The same logic is inlined in .github/workflows/security.yml. It lives here as
well because a copy that can be run locally is worth more than a copy that can
only be read in a workflow file, and the previous version was a hard-coded
comparison of the threshold against itself (80 >= 75), which always exited 0.
A gate that always passes is worse than no gate: it looks like a control in CI
logs while enforcing nothing.

Exits 0 when measured line coverage meets the threshold, 1 when it does not,
and 1 when no report is found or it is unparseable - because "no data" must
never be mistaken for "sufficient coverage".
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def measure(xml_path: Path) -> tuple[int, int]:
    """Return (covered_lines, total_lines) from a Cobertura coverage XML."""
    root = ET.parse(xml_path).getroot()
    covered = 0
    total = 0
    for cls in root.iter("class"):
        for line in cls.iter("line"):
            total += 1
            if line.get("hits", "0").strip() not in ("0", "", "None"):
                covered += 1
    return covered, total


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: coverage_gate.py THRESHOLD [coverage.xml ...]")
        return 2

    threshold = float(sys.argv[1])
    paths = [Path(p) for p in sys.argv[2:]] or [Path("coverage.xml")]

    existing = [p for p in paths if p.exists()]
    if not existing:
        print(f"::error::No coverage report found ({', '.join(str(p) for p in paths)}); "
              "cannot enforce the coverage gate.")
        return 1

    covered_total = 0
    lines_total = 0
    for path in existing:
        try:
            covered, total = measure(path)
        except ET.ParseError as exc:
            print(f"::error::Unparseable coverage XML {path}: {exc}")
            return 1
        covered_total += covered
        lines_total += total
        print(f"{path}: {covered}/{total} lines")

    if lines_total == 0:
        print("::error::Coverage report contains no line elements; "
              "the gate cannot be satisfied by empty data.")
        return 1

    percent = 100.0 * covered_total / lines_total
    print(f"Measured coverage: {percent:.2f}% "
          f"({covered_total}/{lines_total} lines, threshold {threshold}%)")

    if percent < threshold:
        print(f"::error::Coverage {percent:.2f}% is below the required {threshold}%.")
        return 1

    print("Coverage gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
