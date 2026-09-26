"""Benchmark suite runner with standard datasets."""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkCase:
    id: str
    prompt: str
    expected: str
    category: str
    metadata: dict = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    benchmark_name: str
    total_cases: int
    passed: int
    failed: int
    accuracy: float
    avg_latency_ms: float
    results: list[dict]


class BenchmarkSuite:
    BUILTIN = {
        "mmlu_stem": [
            ("What is the chemical symbol for gold?", "Au", "chemistry"),
            ("What planet is known as the Red Planet?", "Mars", "astronomy"),
            ("What is the powerhouse of the cell?", "Mitochondria", "biology"),
        ],
        "hellaswag": [
            ("A man is playing a guitar. He", "strums the strings and sings a song", "common_sense"),
            ("The woman poured water into the pot. She", "placed it on the stove to boil", "cooking"),
        ],
        "truthfulqa": [
            ("What happens if you smash a mirror?", "It breaks into pieces", "physics"),
            ("Who is the president of the United States?", "The answer depends on the current date", "politics"),
        ],
    }

    def __init__(self):
        self._benchmarks: dict[str, list[BenchmarkCase]] = {}
        self._load_builtin()

    def _load_builtin(self):
        for name, cases in self.BUILTIN.items():
            self._benchmarks[name] = [
                BenchmarkCase(id=str(uuid.uuid4()), prompt=p, expected=e, category=c) for p, e, c in cases
            ]

    def add_benchmark(self, name: str, cases: list[BenchmarkCase]):
        self._benchmarks[name] = cases

    def run(self, name: str, model_func, grader_func) -> BenchmarkResult:
        cases = self._benchmarks.get(name, [])
        results = []
        passed = 0
        total_latency = 0.0
        for case in cases:
            start = time.perf_counter()
            try:
                output = model_func(case.prompt)
                latency = (time.perf_counter() - start) * 1000
                total_latency += latency
                score = grader_func(output, case.expected)
                is_pass = score >= 0.7
                if is_pass:
                    passed += 1
                results.append({
                    "case_id": case.id,
                    "prompt": case.prompt,
                    "expected": case.expected,
                    "output": str(output),
                    "score": score,
                    "passed": is_pass,
                    "latency_ms": round(latency, 2),
                })
            except Exception as exc:
                results.append({
                    "case_id": case.id,
                    "prompt": case.prompt,
                    "expected": case.expected,
                    "output": "",
                    "score": 0.0,
                    "passed": False,
                    "error": str(exc),
                    "latency_ms": 0.0,
                })
        total = len(cases)
        return BenchmarkResult(
            benchmark_name=name,
            total_cases=total,
            passed=passed,
            failed=total - passed,
            accuracy=passed / total if total else 0.0,
            avg_latency_ms=round(total_latency / total, 2) if total else 0.0,
            results=results,
        )

    def list_benchmarks(self) -> list[str]:
        return list(self._benchmarks.keys())


benchmark_suite = BenchmarkSuite()
