import subprocess
import sys

sys.path.insert(0, "evals")
from expanded_set import expanded_set

a = [c.id for c in expanded_set() if c.held_out]

code = (
    "import sys; sys.path.insert(0, 'evals');"
    "from expanded_set import expanded_set;"
    "print(','.join(c.id for c in expanded_set() if c.held_out))"
)
r = subprocess.run(["python", "-c", code], capture_output=True, text=True)
b = [x for x in r.stdout.strip().split(",") if x]

print("run1 held-out:", len(a))
print("run2 held-out:", len(b))
print("DETERMINISTIC:", a == b)
assert a == b, "the held-out split is not stable across processes"
