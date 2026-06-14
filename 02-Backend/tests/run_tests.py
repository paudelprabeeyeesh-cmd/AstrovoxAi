"""
Astravox Backend Test Runner
Execute all tests with coverage reporting.
"""

import pytest
import sys
from pathlib import Path

def run_tests(verbose=True, coverage=True):
    """
    Run all backend tests.
    
    Args:
        verbose: Enable verbose output
        coverage: Enable coverage reporting
    
    Returns:
        Exit code
    """
    args = [
        str(Path(__file__).parent),
        "-v" if verbose else "-q",
        "--tb=short",
    ]
    
    if coverage:
        args.extend([
            "--cov=../",
            "--cov-report=html",
            "--cov-report=term-missing",
        ])
    
    return pytest.main(args)


if __name__ == "__main__":
    exit_code = run_tests(verbose=True, coverage=True)
    sys.exit(exit_code)
