import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MetaTask:
    task_id: str
    task_type: str
    features: dict[str, Any]
    optimal_lr: float | None = None
    optimal_batch_size: int | None = None
    performance: float = 0.0
    support_set: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaKnowledgeEntry:
    key: str
    value: Any
    confidence: float = 1.0
    updated_at: float = field(default_factory=time.time)
    source: str = "meta_learner"


class MetaLearningService:
    def __init__(self) -> None:
        self._tasks: dict[str, MetaTask] = {}
        self._meta_knowledge: dict[str, MetaKnowledgeEntry] = {}
        self._client = None
        self._inner_loop_steps: int = 5

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def register_task(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("task_id") or str(uuid.uuid4())
        meta_task = MetaTask(
            task_id=task_id,
            task_type=task.get("task_type", "unknown"),
            features=task.get("features", {}),
            optimal_lr=task.get("optimal_lr"),
            optimal_batch_size=task.get("optimal_batch_size"),
            performance=float(task.get("performance", 0.0)),
            support_set=task.get("support_set", []),
            metadata=task.get("metadata", {}),
        )
        self._tasks[task_id] = meta_task
        logger.info("Registered meta-task %s of type %s", task_id, meta_task.task_type)
        return {"task_id": task_id, "status": "registered"}

    def adapt(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("task_id") or str(uuid.uuid4())
        meta = self._tasks.get(task_id)
        if meta:
            return {
                "task_id": task_id,
                "adapted": True,
                "optimal_lr": meta.optimal_lr,
                "optimal_batch_size": meta.optimal_batch_size,
                "confidence": meta.performance,
            }

        similar = self._find_similar_tasks(task)
        adapted = {
            "task_id": task_id,
            "adapted": True,
            "optimal_lr": self._interpolate(similar, "optimal_lr", default=0.01),
            "optimal_batch_size": self._interpolate(similar, "optimal_batch_size", default=32),
            "confidence": float(task.get("confidence", 0.5)),
            "source_tasks": [s.task_id for s in similar],
        }
        return adapted

    def update_meta_knowledge(self, key: str, value: Any, confidence: float = 1.0, source: str = "meta_learner") -> None:
        entry = MetaKnowledgeEntry(key=key, value=value, confidence=confidence, source=source)
        self._meta_knowledge[key] = entry
        logger.info("Meta-knowledge updated: %s=%.4f (confidence=%.2f)", key, float(value), confidence)

    def get_meta_knowledge(self, key: str) -> Any | None:
        entry = self._meta_knowledge.get(key)
        return entry.value if entry else None

    def inner_loop_update(self, task_id: str, gradients: dict[str, float]) -> dict[str, Any]:
        meta = self._tasks.get(task_id)
        if not meta:
            return {"status": "not_found"}

        updated = dict(gradients)
        for _ in range(self._inner_loop_steps):
            for k in list(updated.keys()):
                updated[k] = updated[k] * 0.9

        meta.optimal_lr = updated.get("lr", meta.optimal_lr)
        meta.optimal_batch_size = int(updated.get("batch_size", meta.optimal_batch_size or 32))
        return {"task_id": task_id, "updated_params": {"lr": meta.optimal_lr, "batch_size": meta.optimal_batch_size}}

    def meta_test(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("task_id") or str(uuid.uuid4())
        adapted = self.adapt(task)
        performance = self._estimate_performance(task, adapted)
        return {
            "task_id": task_id,
            "adapted_params": adapted,
            "estimated_performance": round(performance, 4),
            "confidence": adapted.get("confidence", 0.5),
        }

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        meta = self._tasks.get(task_id)
        if not meta:
            return None
        return {
            "task_id": meta.task_id,
            "task_type": meta.task_type,
            "features": meta.features,
            "optimal_lr": meta.optimal_lr,
            "optimal_batch_size": meta.optimal_batch_size,
            "performance": meta.performance,
            "support_set_size": len(meta.support_set),
        }

    def list_tasks(self, task_type: str | None = None) -> list[dict[str, Any]]:
        tasks = list(self._tasks.values())
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        return [self.get_task(t.task_id) for t in tasks if self.get_task(t.task_id)]

    def _find_similar_tasks(self, task: dict[str, Any], top_k: int = 3) -> list[MetaTask]:
        target_features = task.get("features", {})
        scored = []
        for meta in self._tasks.values():
            similarity = self._cosine_similarity(target_features, meta.features)
            scored.append((similarity, meta))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]

    def _interpolate(self, tasks: list[MetaTask], attr: str, default: Any) -> Any:
        values = [getattr(t, attr) for t in tasks if getattr(t, attr) is not None]
        if not values:
            return default
        if all(isinstance(v, (int, float)) for v in values):
            return sum(values) / len(values)
        return values[0]

    def _cosine_similarity(self, a: dict[str, Any], b: dict[str, Any]) -> float:
        keys = set(a.keys()) | set(b.keys())
        if not keys:
            return 0.0
        dot = sum(float(a.get(k, 0)) * float(b.get(k, 0)) for k in keys)
        norm_a = sum(float(v) ** 2 for v in a.values()) ** 0.5
        norm_b = sum(float(v) ** 2 for v in b.values()) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _estimate_performance(self, task: dict[str, Any], adapted: dict[str, Any]) -> float:
        try:
            prompt = (
                "Estimate the expected performance of the following task given adapted hyperparameters. "
                "Return a float between 0 and 1.\n"
                f"Task: {json.dumps(task)}\nAdapted params: {json.dumps(adapted)}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            value = float((response.choices[0].message.content or "0.5").strip())
            return max(0.0, min(1.0, value))
        except Exception as exc:
            logger.error("Performance estimation failed: %s", exc)
            return 0.5
