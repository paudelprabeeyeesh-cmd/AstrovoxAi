from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AdaptationRecord:
    task_id: str
    before_performance: float
    after_performance: float
    steps: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdaptationTracker:
    def __init__(self):
        self.records: Dict[str, List[AdaptationRecord]] = {}
        self.latest_step: Dict[str, float] = {}

    def record_adaptation(
        self,
        task_id: str,
        before_performance: float,
        after_performance: float,
        steps: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AdaptationRecord:
        record = AdaptationRecord(
            task_id=task_id,
            before_performance=before_performance,
            after_performance=after_performance,
            steps=steps,
            metadata=metadata or {},
        )
        self.records.setdefault(task_id, []).append(record)
        self.latest_step[task_id] = after_performance
        return record

    def record_step(self, task_id: str, performance: float) -> None:
        previous = self.latest_step.get(task_id)
        if previous is not None:
            self.record_adaptation(task_id, previous, performance, steps=1)
        else:
            self.latest_step[task_id] = performance

    def get_adaptation_rate(self, task_id: str) -> float:
        recs = self.records.get(task_id, [])
        if not recs:
            return 0.0
        total_gain = sum(r.after_performance - r.before_performance for r in recs)
        total_steps = sum(r.steps for r in recs)
        if total_steps == 0:
            return 0.0
        return total_gain / total_steps

    def get_convergence_status(self, task_id: str, threshold: float = 0.01) -> Dict[str, Any]:
        recs = self.records.get(task_id, [])
        if len(recs) < 2:
            return {"converged": False, "reason": "insufficient_data"}
        recent = recs[-3:]
        gains = [r.after_performance - r.before_performance for r in recent]
        avg_gain = sum(gains) / len(gains)
        if abs(avg_gain) < threshold:
            return {"converged": True, "avg_gain": avg_gain, "threshold": threshold}
        return {"converged": False, "avg_gain": avg_gain, "threshold": threshold}

    def get_stats(self, task_id: str) -> Dict[str, Any]:
        recs = self.records.get(task_id, [])
        if not recs:
            return {"task_id": task_id, "adaptation_rate": 0.0, "num_records": 0}
        return {
            "task_id": task_id,
            "adaptation_rate": self.get_adaptation_rate(task_id),
            "num_records": len(recs),
            "latest_performance": recs[-1].after_performance,
            "best_performance": max(r.after_performance for r in recs),
        }

    def reset(self, task_id: Optional[str] = None) -> None:
        if task_id is None:
            self.records.clear()
            self.latest_step.clear()
        else:
            self.records.pop(task_id, None)
            self.latest_step.pop(task_id, None)
