"""Summarise the full-suite output by test directory.

The run's output was redirected by PowerShell, which produces UTF-16, so the
encoding is declared explicitly rather than relying on the default.
"""

import re
from collections import Counter
from pathlib import Path


def read_output(path):
    raw = Path(path).read_bytes()
    for encoding in ("utf-16", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


text = read_output("build_output_full.txt")
lines = text.splitlines()

failed = [line for line in lines if line.startswith("FAILED ")]
errors = [line for line in lines if line.startswith("ERROR ")]


def directory_of(nodeid):
    parts = nodeid.replace("\\", "/").split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else parts[0]


failed_counts = Counter(directory_of(line.split()[1]) for line in failed)
error_counts = Counter(directory_of(line.split()[1]) for line in errors)

summary = None
for line in lines:
    if line.startswith("=") and "passed" in line:
        summary = line.strip("= ").strip()
        break

print("summary:", summary)
print("total FAILED:", len(failed), " total ERROR:", len(errors))
print()
print("%-40s %8s %8s" % ("directory", "failed", "error"))
print("-" * 60)
combined = sorted(
    set(failed_counts) | set(error_counts),
    key=lambda d: -(failed_counts[d] + error_counts[d]),
)
for d in combined[:25]:
    print("%-40s %8d %8d" % (d, failed_counts[d], error_counts[d]))

print()
security = failed_counts.get("tests/security", 0) + error_counts.get("tests/security", 0)
print("tests/security failures in this run:", security)
