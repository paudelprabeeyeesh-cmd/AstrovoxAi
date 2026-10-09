from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Prior:
    source_task_id: str
    parameters: Dict[str, float]
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TransferPrior:
    def __init__(self):
        self.priors: Dict[str, Prior] = {}
        self.transfer_history: List[Dict[str, Any]] = []

    def register_prior(self, task_id: str, parameters: Dict[str, float], confidence: float = 1.0) -> None:
        self.priors[task_id] = Prior(
            source_task_id=task_id,
            parameters=dict(parameters),
            confidence=confidence,
        )

    def suggest(self, target_features: Dict[str, float]) -> Optional[Dict[str, float]]:
        if not self.priors:
            return None
        best_prior = None
        best_similarity = -1.0
        for prior in self.priors.values():
            similarity = self._compute_similarity(prior.parameters, target_features)
            if similarity > best_similarity:
                best_similarity = similarity
                best_prior = prior
        if best_prior is None or best_similarity < 0.3:
            return None
        return dict(best_prior.parameters)

    def transfer(self, source_task_id: str, target_task_id: str, similarity: float) -> Dict[str, float]:
        if source_task_id not in self.priors:
            raise KeyError(f"Source task {source_task_id} not found")
        source = self.priors[source_task_id]
        transferred = {k: v * similarity for k, v in source.parameters.items()}
        record = {
            "source": source_task_id,
            "target": target_task_id,
            "similarity": similarity,
            "parameters": transferred,
        }
        self.transfer_history.append(record)
        return transferred

    def decay(self, task_id: str, factor: float) -> None:
        if task_id not in self.priors:
            raise KeyError(f"Task {task_id} not found")
        prior = self.priors[task_id]
        prior.confidence = max(0.0, prior.confidence * factor)
        for key in prior.parameters:
            prior.parameters[key] *= factor

    def get_confidence(self, task_id: str) -> float:
        if task_id not in self.priors:
            raise KeyError(f"Task {task_id} not found")
        return self.priors[task_id].confidence

    def _compute_similarity(self, source_params: Dict[str, float], target_features: Dict[str, float]) -> float:
        shared_keys = set(source_params.keys()) & set(target_features.keys())
        if not shared_keys:
            return 0.0
        diffs = []
        for key in shared_keys:
            sv = source_params[key]
            tv = target_features[key]
            max_val = max(abs(sv), abs(tv), 1.0)
            diffs.append(abs(sv - tv) / max_val)
        avg_diff = sum(diffs) / len(diffs)
        return max(0.0, 1.0 - avg_diff)
