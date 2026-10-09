import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod


class CatastrophicForgettingPrevention(ABC):
    @abstractmethod
    def update(self, model_state: Dict[str, np.ndarray], task_id: str) -> Dict[str, np.ndarray]:
        pass

    @abstractmethod
    def get_importance(self, layer_name: str) -> np.ndarray:
        pass


class EWCMemory(CatastrophicForgettingPrevention):
    def __init__(self, ewc_lambda: float = 100.0):
        self.ewc_lambda = ewc_lambda
        self.optimal_params: Dict[str, np.ndarray] = {}
        self.fisher_information: Dict[str, np.ndarray] = {}
        self.task_count = 0

    def compute_fisher(
        self,
        gradients: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        fisher: Dict[str, np.ndarray] = {}
        for layer_name, grad in gradients.items():
            fisher[layer_name] = np.array(grad ** 2, dtype=np.float64)
        return fisher

    def update(
        self,
        model_state: Dict[str, np.ndarray],
        task_id: str,
        gradients: Optional[Dict[str, np.ndarray]] = None
    ) -> Dict[str, np.ndarray]:
        self.optimal_params = {k: np.array(v) for k, v in model_state.items()}

        if gradients is not None:
            self.fisher_information = self.compute_fisher(gradients)
        else:
            self.fisher_information = {
                k: np.ones_like(v) for k, v in model_state.items()
            }

        self.task_count += 1
        return self.optimal_params

    def get_importance(self, layer_name: str) -> np.ndarray:
        if layer_name not in self.fisher_information:
            return np.zeros(1)
        return self.fisher_information[layer_name]

    def compute_ewc_loss(self, current_state: Dict[str, np.ndarray]) -> float:
        loss = 0.0
        for layer_name, current_params in current_state.items():
            if layer_name in self.optimal_params and layer_name in self.fisher_information:
                diff = current_params - self.optimal_params[layer_name]
                loss += np.sum(self.fisher_information[layer_name] * (diff ** 2))
        return 0.5 * self.ewc_lambda * loss


class ReplayBuffer(CatastrophicForgettingPrevention):
    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self.buffer: List[Tuple[str, Dict[str, np.ndarray]]] = []
        self.task_data: Dict[str, List[Tuple[str, Dict[str, np.ndarray]]]] = {}

    def store_sample(self, task_id: str, sample: Dict[str, np.ndarray]) -> None:
        if len(self.buffer) >= self.buffer_size:
            self.buffer.pop(0)

        self.buffer.append((task_id, sample))

        if task_id not in self.task_data:
            self.task_data[task_id] = []
        self.task_data[task_id].append((task_id, sample))

    def update(self, model_state: Dict[str, np.ndarray], task_id: str) -> Dict[str, np.ndarray]:
        return model_state

    def get_importance(self, layer_name: str) -> np.ndarray:
        total_samples = sum(len(samples) for samples in self.task_data.values())
        if total_samples == 0:
            return np.zeros(1)

        layer_samples = sum(
            1 for task_samples in self.task_data.values()
            for _, sample in task_samples
            if layer_name in sample
        )
        return np.array([layer_samples / total_samples])

    def sample_batch(
        self,
        batch_size: int,
        task_id: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, np.ndarray]]]:
        if task_id is not None:
            available = self.task_data.get(task_id, [])
        else:
            available = self.buffer

        if not available:
            return []

        indices = np.random.choice(
            len(available),
            size=min(batch_size, len(available)),
            replace=False
        )
        return [available[i] for i in indices]

    def get_buffer_stats(self) -> Dict[str, Any]:
        total = sum(len(samples) for samples in self.task_data.values())
        return {
            "total_samples": total,
            "buffer_size": self.buffer_size,
            "utilization": total / self.buffer_size if self.buffer_size > 0 else 0.0,
            "tasks": list(self.task_data.keys()),
            "samples_per_task": {k: len(v) for k, v in self.task_data.items()}
        }
