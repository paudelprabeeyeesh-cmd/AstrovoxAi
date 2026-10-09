"""Test automation framework for AstrovoxAI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent / "02-Backend"
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "web"


def run_backend_tests(coverage: bool = True, markers: str | None = None) -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(BACKEND_DIR / "tests"),
        "-v",
        "--tb=short",
    ]
    if coverage:
        cmd += [
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
        ]
    if markers:
        cmd += ["-m", markers]
    result = subprocess.run(cmd, cwd=BACKEND_DIR)
    return result.returncode


def run_frontend_tests(coverage: bool = True) -> int:
    cmd = ["npm", "run", "test", "--", "--run"]
    if coverage:
        cmd += ["--coverage"]
    result = subprocess.run(cmd, cwd=FRONTEND_DIR, shell=True)
    return result.returncode


def run_lint() -> int:
    backend = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "app", "tests"],
        cwd=BACKEND_DIR,
    )
    frontend = subprocess.run(["npm", "run", "lint"], cwd=FRONTEND_DIR, shell=True)
    return max(backend.returncode, frontend.returncode)


def run_typecheck() -> int:
    frontend = subprocess.run(["npm", "run", "typecheck"], cwd=FRONTEND_DIR, shell=True)
    return frontend.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="AstrovoxAI test automation framework")
    parser.add_argument("--backend", action="store_true", help="Run backend tests")
    parser.add_argument("--frontend", action="store_true", help="Run frontend tests")
    parser.add_argument("--lint", action="store_true", help="Run lint checks")
    parser.add_argument("--typecheck", action="store_true", help="Run type checks")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage")
    parser.add_argument("--markers", default=None, help="Pytest markers to run")
    args = parser.parse_args()

    if not any([args.backend, args.frontend, args.lint, args.typecheck, args.all]):
        parser.print_help()
        return 1

    failures = 0

    if args.all or args.lint:
        print("=" * 60)
        print("Running lint checks...")
        print("=" * 60)
        if run_lint() != 0:
            failures += 1

    if args.all or args.typecheck:
        print("=" * 60)
        print("Running type checks...")
        print("=" * 60)
        if run_typecheck() != 0:
            failures += 1

    if args.all or args.backend:
        print("=" * 60)
        print("Running backend tests...")
        print("=" * 60)
        if run_backend_tests(coverage=not args.no_coverage, markers=args.markers) != 0:
            failures += 1

    if args.all or args.frontend:
        print("=" * 60)
        print("Running frontend tests...")
        print("=" * 60)
        if run_frontend_tests(coverage=not args.no_coverage) != 0:
            failures += 1

    print("=" * 60)
    if failures:
        print(f"FAILED: {failures} check(s) failed")
        return 1
    print("SUCCESS: All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
