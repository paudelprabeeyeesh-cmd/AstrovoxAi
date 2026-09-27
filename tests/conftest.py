import os
import sys

import pytest

# Ensure project root is on path for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def pytest_configure(config):
    config.addinivalue_line("markers", "gpu: mark test as requiring CUDA GPU(s)")
    config.addinivalue_line("markers", "distributed: mark test as requiring distributed setup")
