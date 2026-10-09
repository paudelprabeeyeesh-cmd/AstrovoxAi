import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .catastrophic_forgetting_prevention import EWCMemory


@dataclass
class FisherStatistics:
    layer_name: str
    mean_fisher: float
    std_fisher: float
    max_fisher: float
    min_fisher: float
    sparsity: float


class ElasticWeightConsolidation:
    def __init__(self, ewc_lambda: float = 100.0, fisher_sample_size: int = 1000):
        self.ewc_lambda = ewc_lambda
        self.fisher_sample_size = fisher_sample_size
        self.ewc_memory = EWCMemory(ewc_lambda=ewc_lambda)
        self.task_fisher_history: Dict[str, Dict[str, np.ndarray]] = {}
        self.consolidated_layers: List[str] = []

    def compute_fisher_from_samples(
        self,
        samples: List[Dict[str, np.ndarray]]
    ) -> Dict[str, np.ndarray]:
        if not samples:
            return {}

        fisher_sums: Dict[str, np.ndarray] = {}
        num_samples = max(len(samples), 1)

        for sample in samples:
            for layer_name, activations in sample.items():
                if layer_name not in fisher_sums:
                    fisher_sums[layer_name] = np.zeros_like(activations)
                fisher_sums[layer_name] += activations ** 2

        fisher = {}
        for layer_name, sum_sq in fisher_sums.items():
            fisher[layer_name] = sum_sq / num_samples

        return fisher

    def consolidate_task(
        self,
        task_id: str,
        model_state: Dict[str, np.ndarray],
        samples: Optional[List[Dict[str, np.ndarray]]] = None,
        gradients: Optional[Dict[str, np.ndarray]] = None
    ) -> None:
        if samples is not None:
            fisher = self.compute_fisher_from_samples(samples)
        elif gradients is not None:
            fisher = self.ewc_memory.compute_fisher(gradients)
        else:
            raise ValueError("Must provide either samples or gradients")

        self.task_fisher_history[task_id] = fisher
        self.ewc_memory.update(model_state, task_id, gradients=fisher)

        for layer_name in fisher.keys():
            if layer_name not in self.consolidated_layers:
                self.consolidated_layers.append(layer_name)

    def compute_penalty(
        self,
        current_state: Dict[str, np.ndarray]
    ) -> float:
        return self.ewc_memory.compute_ewc_loss(current_state)

    def get_fisher_statistics(self, task_id: str) -> Dict[str, FisherStatistics]:
        if task_id not in self.task_fisher_history:
            return {}

        stats = {}
        fisher = self.task_fisher_history[task_id]

        for layer_name, values in fisher.items():
            stats[layer_name] = FisherStatistics(
                layer_name=layer_name,
                mean_fisher=float(np.mean(values)),
                std_fisher=float(np.std(values)),
                max_fisher=float(np.max(values)),
                min_fisher=float(np.min(values)),
                sparsity=float(np.sum(values == 0) / values.size)
            )

        return stats

    def get_importance_ranking(
        self,
        task_id: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        if task_id not in self.task_fisher_history:
            return []

        fisher = self.task_fisher_history[task_id]
        importance_scores = [
            (layer_name, float(np.mean(values)))
            for layer_name, values in fisher.items()
        ]
        importance_scores.sort(key=lambda x: x[1], reverse=True)
        return importance_scores[:top_k]

    def adaptive_lambda(
        self,
        current_state: Dict[str, np.ndarray],
        base_lambda: float = 100.0
    ) -> float:
        penalty = self.compute_penalty(current_state)
        if penalty == 0:
            return base_lambda
        return base_lambda * np.log1p(penalty)

    def merge_fisher_matrices(
        self,
        task_ids: List[str],
        method: str = "weighted_average"
    ) -> Dict[str, np.ndarray]:
        if method not in ("weighted_average", "max"):
            raise ValueError(f"Unknown merge method: {method}")

        if not task_ids:
            return {}

        valid_tasks = [tid for tid in task_ids if tid in self.task_fisher_history]
        if not valid_tasks:
            return {}

        if method not in ("weighted_average", "max"):
            raise ValueError(f"Unknown merge method: {method}")

        if method == "weighted_average":
            total_weight = len(valid_tasks)
            merged = {}

            for task_id in valid_tasks:
                for layer_name, fisher in self.task_fisher_history[task_id].items():
                    if layer_name not in merged:
                        merged[layer_name] = np.zeros_like(fisher)
                    merged[layer_name] += fisher / total_weight

            return merged

        elif method == "max":
            merged = {}
            for layer_name in self.consolidated_layers:
                max_fisher = None
                for task_id in valid_tasks:
                    if layer_name in self.task_fisher_history[task_id]:
                        if max_fisher is None:
                            max_fisher = self.task_fisher_history[task_id][layer_name].copy()
                        else:
                            max_fisher = np.maximum(
                                max_fisher,
                                self.task_fisher_history[task_id][layer_name]
                            )
                if max_fisher is not None:
                    merged[layer_name] = max_fisher

            return merged

        else:
            raise ValueError(f"Unknown merge method: {method}")
