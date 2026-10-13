"""Find the pair of modules that crashes pytest together.

Each file passes alone. A crash only appears in a directory run, so the
cause is an interaction between two modules. Test the whole set, then
bisect by dropping candidates, until a minimal crashing set remains.
"""
import subprocess
import sys
from pathlib import Path

BASE = Path("02-Backend")
OUT = Path("_bisect.txt")

files = sorted(
    p.name for p in (BASE / "tests" / "security").glob("*.py")
    if p.name != "__init__.py"
)

BASE_DIR = "02-Backend/tests/security"


def run(names):
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *[f"{BASE_DIR}/{n}" for n in names],
         "-q", "--no-header", "-p", "no:randomly", "--timeout=60"],
        capture_output=True, text=True, cwd=".", timeout=400,
    )
    return r.returncode


lines = []
rc_all = run(files)
lines.append("full set rc=%d (%d files)" % (rc_all, len(files)))
print(lines[-1])

current = files
while len(current) > 1:
    half = len(current) // 2
    halves = [current[:half], current[half:]]
    # Try dropping one side at a time to find a crashing subset.
    found = None
    for side in halves:
        if run(side) != 0:
            found = side
            break
    if found is None:
        # Neither half crashes alone: the pair interacts across halves.
        lines.append("no single-half crash; current=%s" % current)
        print(lines[-1])
        break
    current = found
    lines.append("shrunk to %d files: %s" % (len(current), current))
    print(lines[-1])

lines.append("MINIMAL CRASHING SET: %s" % current)
print(lines[-1])

with OUT.open("w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
