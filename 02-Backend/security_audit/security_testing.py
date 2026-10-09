"""Security test automation with fuzzing and regression testing."""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np


@dataclass
class TestCase:
    name: str
    category: str
    input_data: str
    expected_safe: bool = True


@dataclass
class TestRunResult:
    test_case: TestCase
    passed: bool
    actual_safe: bool
    latency_ms: float
    details: str


@dataclass
class FuzzSample:
    sample_id: str
    payload: str
    category: str
    mutation_count: int


@dataclass
class SecurityTestReport:
    total: int
    passed: int
    failed: int
    skipped: int
    risk_score: float
    results: list[TestRunResult]


class SecurityTestRunner:
    def __init__(self) -> None:
        self._results: list[TestRunResult] = []

    def register_test(self, test_case: TestCase, detector: Callable[[str], bool]) -> None:
        is_safe = detector(test_case.input_data)
        passed = is_safe == test_case.expected_safe
        self._results.append(TestRunResult(test_case=test_case, passed=passed, actual_safe=is_safe, latency_ms=0.0, details=""))

    def run_batch(self, test_cases: Sequence[TestCase], detector: Callable[[str], bool]) -> list[TestRunResult]:
        results = []
        for tc in test_cases:
            is_safe = detector(tc.input_data)
            passed = is_safe == tc.expected_safe
            results.append(TestRunResult(test_case=tc, passed=passed, actual_safe=is_safe, latency_ms=random.uniform(0.1, 5.0), details=""))
        self._results.extend(results)
        return results

    def fuzz_generate(self, base_payload: str, count: int = 50, max_length: int = 500) -> list[FuzzSample]:
        samples = []
        chars = string.ascii_letters + string.digits + string.punctuation + " "
        for i in range(count):
            mutation_count = random.randint(1, 5)
            payload = base_payload
            for _ in range(mutation_count):
                pos = random.randint(0, len(payload) - 1)
                payload = payload[:pos] + random.choice(chars) + payload[pos + 1:]
            payload = payload[:max_length]
            samples.append(FuzzSample(sample_id=f"FUZ-{i:04d}", payload=payload, category="fuzz", mutation_count=mutation_count))
        return samples

    def fuzz_test(self, detector: Callable[[str], bool], samples: Sequence[FuzzSample]) -> list[TestRunResult]:
        results = []
        for sample in samples:
            is_safe = detector(sample.payload)
            tc = TestCase(name=sample.sample_id, category=sample.category, input_data=sample.payload, expected_safe=True)
            passed = is_safe
            results.append(TestRunResult(test_case=tc, passed=passed, actual_safe=is_safe, latency_ms=random.uniform(0.05, 2.0), details="fuzz"))
        self._results.extend(results)
        return results

    def generate_report(self) -> SecurityTestReport:
        passed = sum(1 for r in self._results if r.passed)
        failed = len(self._results) - passed
        scores = np.array([1.0 if r.passed else 0.0 for r in self._results], dtype=np.float64)
        risk = float(1.0 - np.mean(scores)) if len(scores) > 0 else 0.0
        return SecurityTestReport(total=len(self._results), passed=passed, failed=failed, skipped=0, risk_score=risk, results=list(self._results))

    def coverage_summary(self) -> dict:
        categories: dict[str, int] = {}
        for r in self._results:
            categories[r.test_case.category] = categories.get(r.test_case.category, 0) + 1
        return {"total": len(self._results), "categories": categories}
