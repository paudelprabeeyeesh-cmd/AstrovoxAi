"""Bisect which module in tests/security crashes the interpreter.

Run each file in its own subprocess so one native crash does not hide the
rest. A pytest directory run exits -1073741819 (0xC0000005) with no output,
which points at a native extension rather than a Python assertion.
"""
import subprocess
import sys
from pathlib import Path

BASE = Path("02-Backend")
OUT = Path("_bisect.txt")

import os
files = sorted(
    p.name for p in (BASE / "tests" / "security").glob("*.py")
    if p.name != "__init__.py"
)

rows = []
for name in files:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", f"tests/security/{name}", "-q",
         "--no-header", "-p", "no:randomly", "--timeout=60"],
        capture_output=True, text=True, cwd=str(BASE), timeout=240,
    )
    out = (r.stdout or "") + (r.stderr or "")
    tail = out.strip().split("\n")
    summary = tail[-1][:96] if tail and out.strip() else ""
    rows.append((name, r.returncode, summary))

with OUT.open("w", encoding="utf-8") as fh:
    for name, rc, summary in rows:
        fh.write("%14d  %-34s %s\n" % (rc, name, summary))

for name, rc, summary in rows:
    print(rc, name, summary)
