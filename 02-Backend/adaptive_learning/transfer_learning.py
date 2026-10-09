import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class TransferLearner:
    def __init__(self, base_model: Optional[Dict[str, np.ndarray]] = None):
        self.base_model = base_model if base_model is not None else {}
        self.frozen_layers: List[str] = []
        self.fine_tuned_layers: List[str] = []
        self.transfer_history: List[Dict[str, Any]] = []

    def load_base(self, model_state: Dict[str, np.ndarray]) -> None:
        self.base_model = {k: np.array(v) for k, v in model_state.items()}

    def freeze_layers(self, layer_names: List[str]) -> None:
        for name in layer_names:
            if name not in self.frozen_layers:
                self.frozen_layers.append(name)
            if name in self.fine_tuned_layers:
                self.fine_tuned_layers.remove(name)

    def unfreeze_layers(self, layer_names: List[str]) -> None:
        for name in layer_names:
            if name in self.frozen_layers:
                self.frozen_layers.remove(name)
            if name not in self.fine_tuned_layers and name in self.base_model:
                self.fine_tuned_layers.append(name)

    def transfer(self, target_task_data: Dict[str, np.ndarray], fine_tune_lr: float = 0.001, steps: int = 10) -> Dict[str, np.ndarray]:
        model = {k: np.array(v) for k, v in self.base_model.items()}
        for step in range(steps):
            loss, grad = self._compute_loss_and_grad(model, target_task_data)
            for name, g in grad.items():
                if name not in self.frozen_layers:
                    model[name] -= fine_tune_lr * g
            self.transfer_history.append({"step": step, "loss": float(loss)})
        return model

    def _compute_loss_and_grad(self, model: Dict[str, np.ndarray], data: Dict[str, np.ndarray]) -> Tuple[float, Dict[str, np.ndarray]]:
        loss = 0.0
        grad: Dict[str, np.ndarray] = {}
        for name, params in model.items():
            if name in data:
                target = data[name]
                diff = params - target
                loss += float(np.sum(diff ** 2))
                grad[name] = 2.0 * diff / max(len(diff), 1)
        return loss, grad

    def adapt_domain(self, source_features: np.ndarray, target_features: np.ndarray, num_components: int = 10) -> np.ndarray:
        source_features = np.atleast_2d(source_features)
        target_features = np.atleast_2d(target_features)
        d = min(num_components, source_features.shape[1], target_features.shape[1])
        _, s_s, _ = np.linalg.svd(source_features, full_matrices=False)
        _, s_t, _ = np.linalg.svd(target_features, full_matrices=False)
        M = np.diag(s_s[:d]) @ np.diag(1.0 / (s_t[:d] + 1e-12))
        return M

    def get_transfer_report(self) -> Dict[str, Any]:
        if not self.transfer_history:
            return {"steps": 0, "final_loss": None}
        return {
            "steps": len(self.transfer_history),
            "final_loss": self.transfer_history[-1]["loss"],
            "initial_loss": self.transfer_history[0]["loss"],
            "improvement": self.transfer_history[0]["loss"] - self.transfer_history[-1]["loss"],
        }
