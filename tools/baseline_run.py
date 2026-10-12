"""Run a time-boxed baseline over the test areas this work touched.

The full 6,511-test suite does not complete inside a usable wall-clock
window: several chunks make real network calls or wait on a condition that
never fires, so a single run dies at a timeout before printing a summary.
This runs the areas that matter for a security and correctness baseline,
records what completed, and is explicit about what did not.

Usage: python tools/baseline_run.py [chunk ...]
"""
import re
import subprocess
import sys
import time

WORKDIR = "02-Backend"

# The chunks that carry the security and product-path guarantees.
DEFAULT_CHUNKS = [
    ("tests/security", None),
    ("tests/integration", None),
    ("tests/unit", None),
]


def run(paths, timeout=240):
    started = time.time()
    r = subprocess.run(
        ["python", "-m", "pytest", "-q", "--no-header", "--timeout=20",
         "-p", "no:randomly", *paths],
        capture_output=True, text=True, cwd=WORKDIR, timeout=timeout,
    )
    return r.stdout + "\n" + r.stderr, time.time() - started


def parse(out):
    summary = ""
    for line in out.splitlines():
        s = line.strip().strip("=").strip()
        if re.search(r"\b\d+ (passed|failed|error)\b", s):
            summary = s
    return summary


def main():
    chunks = sys.argv[1:] or [c[0] for c in DEFAULT_CHUNKS]
    totals = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "xfailed": 0}
    rows = []
    hung = []

    for chunk in chunks:
        try:
            out, took = run([chunk])
        except subprocess.TimeoutExpired:
            hung.append(chunk)
            rows.append(f"HUNG   {chunk:34s} exceeded {240}s")
            print(f"HUNG   {chunk:34s} > 240s")
            continue
        summary = parse(out)
        if not summary:
            rows.append(f"NONE   {chunk:34s} no summary (likely no tests)")
            print(f"NONE   {chunk:34s} no summary")
            continue
        for key in totals:
            m = re.search(rf"(\d+) {key}", summary)
            if m:
                totals[key] += int(m.group(1))
        rows.append(f"OK     {chunk:34s} {summary}")
        print(f"OK     {chunk:34s} {summary[:70]:<70s} ({took:.0f}s)")

    print()
    print("TOTALS", totals)
    if hung:
        print("HUNG  ", hung)

    with open("_baseline.txt", "w", encoding="utf-8") as fh:
        fh.write("chunks run:\n")
        for c in chunks:
            fh.write(f"  {c}\n")
        fh.write("\nTOTALS " + str(totals) + "\n")
        if hung:
            fh.write("HUNG " + str(hung) + "\n")
        fh.write("\n" + "\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
