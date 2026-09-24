"""
Test verification for load test concurrency.
"""

from tests.load_test import test_load_test_concurrency


def test_load_test_concurrency_entry() -> None:
    test_load_test_concurrency()
