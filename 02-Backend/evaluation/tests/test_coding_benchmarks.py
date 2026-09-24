
from app.evaluation.coding_benchmarks import CodingBenchmarks


def _runner(prompt: str) -> str:
    if "sum of two numbers" in prompt:
        return "def add(a, b):\n    return a + b"
    if "palindrome" in prompt:
        return "def is_palindrome(s):\n    return s == s[::-1]"
    if "binary search" in prompt:
        return "def binary_search(arr, target):\n    low, high = 0, len(arr)-1\n    while low <= high:\n        mid = (low+high)//2\n        return mid\n    return -1"
    if "sort a list" in prompt:
        return "def sort_list(lst):\n    return sorted(lst)"
    if "reverse a linked list" in prompt:
        return "def reverse_list(head):\n    prev = None\n    curr = head\n    while curr:\n        nxt = curr.next\n        curr.next = prev\n        prev = curr\n        curr = nxt\n    return prev"
    return ""


def test_coding_benchmark_run():
    bench = CodingBenchmarks()
    result = bench.run_benchmark(_runner)
    assert result["benchmark"] == "coding"
    assert result["total"] == 5
    assert result["passed"] >= 3
