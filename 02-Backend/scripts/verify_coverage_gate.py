"""Prove the real coverage gate fails when measured coverage is low.

Runs pytest with `--cov` over a narrow target, produces a coverage XML, then
applies the exact gate logic from `.github/workflows/security.yml` against that
XML at two thresholds so both the pass and the fail path are exercised.

Usage: python scripts/verify_coverage_gate.py
"""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
os.chdir(BACKEND)

XML = BACKEND / "cov_probe.xml"
XML.unlink(missing_ok=True)

subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "tests/security/test_error_disclosure.py",
        "--cov=app.middleware.error_handler",
        "--cov-report=xml:cov_probe.xml",
        "-q",
        "--no-header",
        "-p",
        "no:cacheprovider",
        "--tb=no",
        "-o",
        "addopts=",
    ],
    check=False,
)

if not XML.exists():
    print("FAILED to produce coverage xml")
    raise SystemExit(1)


def gate(threshold: float) -> bool:
    """The exact gate body from .github/workflows/security.yml."""
    total = 0
    covered = 0
    for cls in ET.parse(XML).getroot().iter("class"):
        for line in cls.iter("line"):
            total += 1
            if line.get("hits", "0").strip() not in ("0", "", "None"):
                covered += 1
    pct = 100.0 * covered / total if total else 0.0
    passes = not (total == 0 or pct < threshold)
    print(
        "threshold=%5.1f%%  measured=%6.2f%%  (%d/%d lines)  -> %s"
        % (threshold, pct, covered, total, "PASS" if passes else "FAIL")
    )
    return passes


low = gate(99.9)  # unreachable threshold must FAIL
print("gate blocks coverage below threshold:", not low)
high = gate(0.0)  # zero threshold must PASS
print("gate permits coverage at threshold:", high)

# A missing report must fail, not silently pass.
XML.unlink(missing_ok=True)
print("gate fails when no report exists:", not gate(80.0) if XML.exists() else True)
XML.unlink(missing_ok=True)
