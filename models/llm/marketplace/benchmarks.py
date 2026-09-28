import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    result_id: str
    benchmark_id: str
    submission_id: str
    model_id: str
    metrics: Dict[str, float]
    submitted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BenchmarkSubmission:
    submission_id: str
    benchmark_id: str
    submitter_id: str
    model_id: str
    results: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    submitted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BenchmarkDefinition:
    benchmark_id: str
    name: str
    description: str
    metrics: List[str]
    owner_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)


class BenchmarkManager:
    def __init__(self) -> None:
        self._benchmarks: Dict[str, BenchmarkDefinition] = {}
        self._submissions: Dict[str, List[BenchmarkSubmission]] = {}
        self._results: Dict[str, List[BenchmarkResult]] = {}

    def create_benchmark(
        self,
        name: str,
        description: str,
        metrics: List[str],
        owner_id: str,
    ) -> BenchmarkDefinition:
        benchmark_id = str(uuid.uuid4())
        benchmark = BenchmarkDefinition(
            benchmark_id=benchmark_id,
            name=name,
            description=description,
            metrics=metrics,
            owner_id=owner_id,
        )
        self._benchmarks[benchmark_id] = benchmark
        self._submissions[benchmark_id] = []
        self._results[benchmark_id] = []
        logger.info("Created benchmark %s", name)
        return benchmark

    def submit_result(
        self,
        benchmark_id: str,
        submitter_id: str,
        model_id: str,
        results: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkSubmission:
        if benchmark_id not in self._benchmarks:
            raise KeyError(f"Benchmark not found: {benchmark_id}")
        submission = BenchmarkSubmission(
            submission_id=str(uuid.uuid4()),
            benchmark_id=benchmark_id,
            submitter_id=submitter_id,
            model_id=model_id,
            results=results,
            metadata=metadata or {},
        )
        self._submissions[benchmark_id].append(submission)
        result = BenchmarkResult(
            result_id=str(uuid.uuid4()),
            benchmark_id=benchmark_id,
            submission_id=submission.submission_id,
            model_id=model_id,
            metrics=results,
        )
        self._results[benchmark_id].append(result)
        logger.info("Submitted results for benchmark %s", benchmark_id)
        return submission

    def generate_leaderboard(self, benchmark_id: str, metric: str, ascending: bool = False) -> List[Dict[str, Any]]:
        if benchmark_id not in self._benchmarks:
            raise KeyError(f"Benchmark not found: {benchmark_id}")
        results = self._results[benchmark_id]
        entries = []
        for r in results:
            if metric in r.metrics:
                entries.append({
                    "model_id": r.model_id,
                    "score": r.metrics[metric],
                    "submitted_at": r.submitted_at.isoformat(),
                })
        entries.sort(key=lambda x: x["score"], reverse=not ascending)
        return entries

    def get_benchmark(self, benchmark_id: str) -> BenchmarkDefinition:
        if benchmark_id not in self._benchmarks:
            raise KeyError(f"Benchmark not found: {benchmark_id}")
        return self._benchmarks[benchmark_id]

    def list_benchmarks(self) -> List[BenchmarkDefinition]:
        return list(self._benchmarks.values())
