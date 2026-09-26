"""Human evaluation workflows."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class HumanEvalTask:
    id: str
    prompt: str
    response: str
    criteria: list[str] = field(default_factory=list)
    status: str = "open"
    metadata: dict = field(default_factory=dict)


@dataclass
class Rating:
    task_id: str
    rater_id: str
    score: float
    feedback: str = ""
    criteria_scores: dict = field(default_factory=dict)


class HumanEvaluationManager:
    def __init__(self):
        self._tasks: dict[str, HumanEvalTask] = {}

    def create_task(self, prompt: str, response: str, criteria: Optional[list[str]] = None, metadata: Optional[dict] = None) -> HumanEvalTask:
        task_id = str(uuid.uuid4())
        task = HumanEvalTask(
            id=task_id,
            prompt=prompt,
            response=response,
            criteria=criteria or ["accuracy", "coherence", "relevance"],
            metadata=metadata or {},
        )
        self._tasks[task_id] = task
        self._persist(task)
        return task

    def _persist(self, task: HumanEvalTask):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO human_eval_tasks (id, prompt, response, criteria, status, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task.id,
                    task.prompt,
                    task.response,
                    json.dumps(task.criteria),
                    task.status,
                    json.dumps(task.metadata),
                ),
            )
            conn.commit()

    def submit_rating(self, task_id: str, rater_id: str, score: float, feedback: str = "", criteria_scores: Optional[dict] = None) -> Rating:
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        rating = Rating(
            task_id=task_id,
            rater_id=rater_id,
            score=score,
            feedback=feedback,
            criteria_scores=criteria_scores or {},
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO human_eval_ratings (id, task_id, rater_id, score, feedback, criteria_scores) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    task_id,
                    rater_id,
                    score,
                    feedback,
                    json.dumps(criteria_scores or {}),
                ),
            )
            conn.commit()
        return rating

    def aggregate_results(self, task_id: str) -> dict:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT score, feedback, criteria_scores FROM human_eval_ratings WHERE task_id = ?",
                (task_id,),
            ).fetchall()
        if not rows:
            return {"mean_score": 0.0, "std": 0.0, "count": 0}
        scores = [r["score"] for r in rows]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std = variance ** 0.5
        return {
            "mean_score": round(mean, 3),
            "std": round(std, 3),
            "count": len(scores),
            "feedback_samples": [r["feedback"] for r in rows if r["feedback"]][:5],
        }

    def inter_annotator_agreement(self, task_id: str) -> dict:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT rater_id, score FROM human_eval_ratings WHERE task_id = ?",
                (task_id,),
            ).fetchall()
        if not rows:
            return {"kappa": 0.0, "agreement": "none"}
        rater_scores: dict[str, list[float]] = {}
        for r in rows:
            rater_scores.setdefault(r["rater_id"], []).append(r["score"])
        if len(rater_scores) < 2:
            return {"kappa": 1.0, "agreement": "single_rater"}
        all_scores = [s for scores in rater_scores.values() for s in scores]
        mean_all = sum(all_scores) / len(all_scores)
        numerator = sum((s - mean_all) ** 2 for s in all_scores)
        denominator = sum((s - mean_all) ** 2 for scores in rater_scores.values() for s in scores)
        kappa = 1.0 - (numerator / denominator) if denominator else 1.0
        return {"kappa": round(kappa, 3), "agreement": "substantial" if kappa > 0.6 else "moderate"}


human_eval_manager = HumanEvaluationManager()
