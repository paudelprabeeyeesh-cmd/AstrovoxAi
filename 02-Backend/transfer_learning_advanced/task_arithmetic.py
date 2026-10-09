import numpy as np
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class MergeMethod(Enum):
    WEIGHTED_AVERAGE = "weighted_average"
    TASK_ARITHMETIC = "task_arithmetic"
    MODEL_SOUP = "model_soup"
    TIES_MERGING = "ties_merging"


@dataclass
class TaskVector:
    task_id: str
    source_model: Dict[str, np.ndarray]
    target_model: Dict[str, np.ndarray]
    scaling: float = 1.0

    def vector(self) -> Dict[str, np.ndarray]:
        return {
            k: self.scaling * (self.target_model.get(k, np.zeros_like(v)) - v)
            for k, v in self.source_model.items()
        }

    def scale(self, factor: float) -> "TaskVector":
        self.scaling = factor
        return self


@dataclass
class MergeConfig:
    method: MergeMethod = MergeMethod.WEIGHTED_AVERAGE
    scaling: float = 1.0
    normalize: bool = False
    exclude_keys: List[str] = field(default_factory=list)


class TaskArithmetic:
    def __init__(self):
        self.task_vectors: List[TaskVector] = []
        self.finetuned_models: Dict[str, Dict[str, np.ndarray]] = {}

    def add_task_vector(self, task_vector: TaskVector) -> None:
        self.task_vectors.append(task_vector)

    def set_finetuned(self, task_id: str, model: Dict[str, np.ndarray]) -> None:
        self.finetuned_models[task_id] = {k: v.copy() for k, v in model.items()}

    def get_task_vector(self, task_id: str, base_model: Dict[str, np.ndarray]) -> TaskVector:
        if task_id not in self.finetuned_models:
            raise KeyError(f"Unknown task: {task_id}")
        return TaskVector(task_id=task_id, source_model=base_model, target_model=self.finetuned_models[task_id])

    def merge(
        self,
        base_model: Dict[str, np.ndarray],
        config: Optional[MergeConfig] = None
    ) -> Dict[str, np.ndarray]:
        config = config or MergeConfig()
        if config.method == MergeMethod.WEIGHTED_AVERAGE:
            return self._weighted_average(base_model, config)
        elif config.method == MergeMethod.TASK_ARITHMETIC:
            return self._task_arithmetic(base_model, config)
        elif config.method == MergeMethod.MODEL_SOUP:
            return self._model_soup(base_model, config)
        elif config.method == MergeMethod.TIES_MERGING:
            return self._ties_merging(base_model, config)
        else:
            raise ValueError(f"Unknown merge method: {config.method}")

    def _weighted_average(self, base_model: Dict[str, np.ndarray], config: MergeConfig) -> Dict[str, np.ndarray]:
        if not self.task_vectors:
            return {k: v.copy() for k, v in base_model.items()}
        merged = {}
        for tv in self.task_vectors:
            vec = tv.vector()
            for k, v in vec.items():
                if k in config.exclude_keys:
                    continue
                merged[k] = merged.get(k, 0.0) + v
        n = len(self.task_vectors)
        result = {}
        for k in base_model:
            if k in config.exclude_keys:
                result[k] = base_model[k].copy()
            else:
                avg = merged.get(k, np.zeros_like(base_model[k])) / n
                result[k] = base_model[k] + avg if not config.normalize else avg
        return result

    def _task_arithmetic(self, base_model: Dict[str, np.ndarray], config: MergeConfig) -> Dict[str, np.ndarray]:
        if not self.task_vectors:
            return {k: v.copy() for k, v in base_model.items()}
        merged = {}
        for tv in self.task_vectors:
            vec = tv.vector()
            for k, v in vec.items():
                if k in config.exclude_keys:
                    continue
                merged[k] = merged.get(k, 0.0) + v * config.scaling
        result = {}
        for k in base_model:
            if k in config.exclude_keys:
                result[k] = base_model[k].copy()
            else:
                delta = merged.get(k, np.zeros_like(base_model[k]))
                result[k] = base_model[k] + delta
        return result

    def _model_soup(self, base_model: Dict[str, np.ndarray], config: MergeConfig) -> Dict[str, np.ndarray]:
        models = [self.finetuned_models[tv.task_id] for tv in self.task_vectors if tv.task_id in self.finetuned_models]
        if not models:
            return {k: v.copy() for k, v in base_model.items()}
        result = {}
        for k in base_model:
            if k in config.exclude_keys:
                result[k] = base_model[k].copy()
            else:
                stacked = np.stack([m.get(k, base_model[k]) for m in models])
                result[k] = np.mean(stacked, axis=0)
        return result

    def _ties_merging(self, base_model: Dict[str, np.ndarray], config: MergeConfig) -> Dict[str, np.ndarray]:
        task_vecs = [tv.vector() for tv in self.task_vectors]
        if not task_vecs:
            return {k: v.copy() for k, v in base_model.items()}
        merged = {}
        for vec in task_vecs:
            for k, v in vec.items():
                if k in config.exclude_keys:
                    continue
                sign = np.sign(v)
                mag = np.abs(v)
                if k not in merged:
                    merged[k] = {"sign": sign.copy(), "mag": mag.copy(), "count": np.ones_like(mag, dtype=int)}
                else:
                    merged[k]["count"] += 1
                    mask = mag > merged[k]["mag"]
                    merged[k]["mag"] = np.where(mask, mag, merged[k]["mag"])
                    merged[k]["sign"] = np.where(mask, sign, merged[k]["sign"])
        result = {}
        for k in base_model:
            if k in config.exclude_keys:
                result[k] = base_model[k].copy()
            elif k in merged:
                result[k] = base_model[k] + merged[k]["sign"] * merged[k]["mag"] * config.scaling
            else:
                result[k] = base_model[k].copy()
        return result

    def merge_report(self, base_model: Dict[str, np.ndarray]) -> Dict[str, Any]:
        merged = self.merge(base_model)
        diff_norm = 0.0
        count = 0
        for k in merged:
            if k not in base_model:
                continue
            diff = merged[k] - base_model[k]
            diff_norm += float(np.sum(diff ** 2))
            count += diff.size
        return {
            "merged_params": len(merged),
            "avg_param_change": diff_norm / max(count, 1),
            "task_vectors_count": len(self.task_vectors)
        }
