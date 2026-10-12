import subprocess
import sys

results = []


def run(label, cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    out = r.stdout + r.stderr
    tail = [l for l in out.splitlines() if l.strip()]
    results.append((label, r.returncode, tail[-1] if tail else "(no output)"))
    print("%-22s rc=%d  %s" % (label, r.returncode, (tail[-1][:80] if tail else "")))


run("compose hardening", [sys.executable, "tools/verify_compose.py"])
run("secret scan", [sys.executable, "tools/secret_scan.py"])
run("eval split stable", [sys.executable, "tools/check_split.py"])
run("go: build + vet + test", [
    "go", "test", "./...", "-count=1",
], cwd=None)
run("security tests", [sys.executable, "-m", "pytest", "tests/security",
                       "-q", "--no-header", "--timeout=90", "-p", "no:randomly"],
    cwd="02-Backend")
run("eval tests", [sys.executable, "-m", "pytest", "evals",
                   "-q", "--no-header", "-p", "no:cacheprovider"])

print()
ok = all(rc == 0 for _l, rc, _o in results)
print("ALL GREEN" if ok else "SOME FAILED")
