"""
conftest.py for product_polish/tests

Makes product_polish importable from both:
- pytest -q  (cwd == tests/)
- pytest product_polish/tests/
"""

import os
import sys

# Absolute path to 02-Backend
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)

# conftest.py only
