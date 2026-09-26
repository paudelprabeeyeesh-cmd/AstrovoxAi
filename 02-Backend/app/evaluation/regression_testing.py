"""Regression testing framework for model output stability."""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class RegressionCase:
    id: str
    name: str
    prompt: str
    baseline_output: str
    tolerance: float = 0.1
    metadata: dict = field(default_factory=dict)


@dataclass
class RegressionResult:
    case_id: str
    passed: bool
    delta_score: float
    baseline_length: int
    current_length: int
    diff_summary: str
    latency_ms: float


class RegressionTestSuite:
    def __init__(self):
        self._cases: dict[str, RegressionCase] = {}
        self._load_persisted()

    def _load_persisted(self):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, name, prompt, baseline_output, tolerance, metadata FROM regression_cases"
            ).fetchall()
            for r in rows:
                self._cases[r["id"]] = RegressionCase(
                    id=r["id"],
                    name=r["name"],
                    prompt=r["prompt"],
                    baseline_output=r["baseline_output"],
                    tolerance=float(r["tolerance"] or 0.1),
                    metadata=json.loads(r["metadata"] or "{}"),
                )

    def add_case(
        self,
        name: str,
        prompt: str,
        baseline_output: str,
        tolerance: float = 0.1,
        metadata: Optional[dict] = None,
    ) -> RegressionCase:
        case_id = str(uuid.uuid4())
        case = RegressionCase(
            id=case_id,
            name=name,
            prompt=prompt,
            baseline_output=baseline_output,
            tolerance=tolerance,
            metadata=metadata or {},
        )
        self._cases[case_id] = case
        self._persist(case)
        return case

    def _persist(self, case: RegressionCase):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO regression_cases (id, name, prompt, baseline_output, tolerance, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    case.id,
                    case.name,
                    case.prompt,
                    case.baseline_output,
                    case.tolerance,
                    json.dumps(case.metadata),
                ),
            )
            conn.commit()

    def run(self, model_func, case_ids: Optional[list[str]] = None) -> list[RegressionResult]:
        results = []
        targets = case_ids or list(self._cases.keys())
        for cid in targets:
            case = self._cases.get(cid)
            if not case:
                continue
            start = time.perf_counter()
            try:
                current_output = model_func(case.prompt)
            except Exception as exc:
                results.append(
                    RegressionResult(
                        case_id=cid,
                        passed=False,
                        delta_score=1.0,
                        baseline_length=len(case.baseline_output),
                        current_length=0,
                        diff_summary=str(exc),
                        latency_ms=0.0,
                    )
                )
                continue
            latency = (time.perf_counter() - start) * 1000
            delta = self._compute_delta(case.baseline_output, current_output)
            passed = delta <= case.tolerance
            results.append(
                RegressionResult(
                    case_id=cid,
                    passed=passed,
                    delta_score=delta,
                    baseline_length=len(case.baseline_output),
                    current_length=len(current_output),
                    diff_summary=self._summarize_diff(case.baseline_output, current_output),
                    latency_ms=round(latency, 2),
                )
            )
        return results

    def _compute_delta(self, baseline: str, current: str) -> float:
        if not baseline and not current:
            return 0.0
        if not baseline or not current:
            return 1.0
        baseline_words = set(baseline.lower().split())
        current_words = set(current.lower().split())
        if not baseline_words:
            return 0.0 if not current_words else 1.0
        overlap = len(baseline_words & current_words)
        return 1.0 - (overlap / len(baseline_words))

    def _summarize_diff(self, baseline: str, current: str) -> str:
        if baseline == current:
            return "identical"
        b_set = set(baseline.lower().split())
        c_set = set(current.lower().split())
        added = c_set - b_set
        removed = b_set - c_set
        return f"added={len(added)} removed={len(removed)}"

    def list_cases(self) -> list[dict]:
        return [{"id": c.id, "name": c.name, "prompt": c.prompt[:100]} for c in self._cases.values()]


regression_suite = RegressionTestSuite()
