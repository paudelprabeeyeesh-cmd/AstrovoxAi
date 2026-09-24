import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class ActiveLearner:
    def __init__(self, strategy: str = "uncertainty"):
        self.strategy = strategy
        self.labeled_x: np.ndarray = np.empty((0, 0))
        self.labeled_y: np.ndarray = np.empty((0,), dtype=int)
        self.unlabeled_x: Optional[np.ndarray] = None
        self.unlabeled_indices: np.ndarray = np.empty(0, dtype=int)
        self.classes: np.ndarray = np.empty(0, dtype=int)
        self.query_log: List[Dict[str, Any]] = []

    def initialize(self, x: np.ndarray, initial_labels: Optional[np.ndarray] = None) -> None:
        self.unlabeled_x = x
        self.unlabeled_indices = np.arange(len(x))
        self.classes = np.unique(initial_labels) if initial_labels is not None else np.array([0, 1])
        if initial_labels is not None and len(initial_labels) > 0:
            self.labeled_x = x[initial_labels != -1] if -1 in initial_labels else x[:1]
            self.labeled_y = initial_labels[initial_labels != -1] if -1 in initial_labels else initial_labels[:1]
            mask = np.ones(len(x), dtype=bool)
            if -1 in initial_labels:
                mask[initial_labels != -1] = False
            self.unlabeled_indices = np.where(mask)[0]
            self.unlabeled_x = x[mask]

    def query(self, model: Any, batch_size: int = 1) -> List[int]:
        if self.strategy == "uncertainty":
            return self._uncertainty_sampling(model, batch_size)
        elif self.strategy == "entropy":
            return self._entropy_sampling(model, batch_size)
        elif self.strategy == "margin":
            return self._margin_sampling(model, batch_size)
        elif self.strategy == "random":
            return self._random_sampling(batch_size)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _get_scores(self, model: Any) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(self.unlabeled_x)
        elif hasattr(model, "classify"):
            proba = np.zeros((len(self.unlabeled_x), len(self.classes)))
            preds = model.classify(self.unlabeled_x)
            for i, p in enumerate(preds):
                proba[i, p % len(self.classes)] = 1.0
        else:
            proba = np.random.rand(len(self.unlabeled_x), max(len(self.classes), 2))
        return proba

    def _uncertainty_sampling(self, model: Any, batch_size: int) -> List[int]:
        proba = self._get_scores(model)
        uncertainties = 1.0 - np.max(proba, axis=1)
        indices = np.argsort(uncertainties)[::-1][:batch_size]
        return [int(self.unlabeled_indices[i]) for i in indices]

    def _entropy_sampling(self, model: Any, batch_size: int) -> List[int]:
        proba = self._get_scores(model)
        eps = 1e-12
        entropy = -np.sum(proba * np.log(proba + eps), axis=1)
        indices = np.argsort(entropy)[::-1][:batch_size]
        return [int(self.unlabeled_indices[i]) for i in indices]

    def _margin_sampling(self, model: Any, batch_size: int) -> List[int]:
        proba = self._get_scores(model)
        sorted_proba = np.sort(proba, axis=1)
        margin = sorted_proba[:, -1] - sorted_proba[:, -2]
        indices = np.argsort(margin)[:batch_size]
        return [int(self.unlabeled_indices[i]) for i in indices]

    def _random_sampling(self, batch_size: int) -> List[int]:
        if len(self.unlabeled_indices) == 0:
            return []
        indices = np.random.choice(len(self.unlabeled_indices), size=min(batch_size, len(self.unlabeled_indices)), replace=False)
        return [int(self.unlabeled_indices[i]) for i in indices]

    def update_labels(self, indices: List[int], labels: np.ndarray) -> None:
        for idx, label in zip(indices, labels):
            self.query_log.append({"index": int(idx), "label": int(label)})
            if idx in self.unlabeled_indices:
                pos = np.where(self.unlabeled_indices == idx)[0]
                if len(pos) > 0:
                    self.unlabeled_indices = np.delete(self.unlabeled_indices, pos[0])
        if len(self.unlabeled_indices) == 0:
            self.unlabeled_x = np.empty((0, self.unlabeled_x.shape[1])) if self.unlabeled_x is not None else np.empty((0, 0))

    def get_query_efficiency(self) -> Dict[str, Any]:
        return {
            "labeled_count": len(self.labeled_y),
            "unlabeled_count": len(self.unlabeled_indices),
            "queries": len(self.query_log),
            "strategy": self.strategy,
        }
