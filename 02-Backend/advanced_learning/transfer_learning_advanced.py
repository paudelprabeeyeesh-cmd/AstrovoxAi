import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class TransferConfig:
    input_dim: int
    output_dim: int
    hidden_dim: int = 128
    num_layers: int = 3
    fine_tune_lr: float = 0.001
    unfreeze_schedule: List[int] = field(default_factory=lambda: [5, 10, 15])
    adaptation_lambda: float = 0.1


class AdvancedTransferLearner:
    def __init__(self, config: TransferConfig):
        self.config = config
        self.base_params: Dict[str, np.ndarray] = {}
        self.task_params: Dict[str, np.ndarray] = {}
        self.frozen_layers: List[int] = []
        self.transfer_history: List[Dict[str, Any]] = []
        self.step_count: int = 0
        self._initialize_params()

    def _initialize_params(self) -> None:
        dims = [self.config.input_dim] + [self.config.hidden_dim] * (self.config.num_layers - 1) + [self.config.output_dim]
        for i in range(len(dims) - 1):
            self.base_params[f'W{i}'] = np.random.randn(dims[i], dims[i + 1]).astype(np.float64) * np.sqrt(2.0 / dims[i])
            self.base_params[f'b{i}'] = np.zeros(dims[i + 1], dtype=np.float64)
        self.task_params = {k: v.copy() for k, v in self.base_params.items()}

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _relu_grad(x: np.ndarray) -> np.ndarray:
        return (x > 0).astype(np.float64)

    def _forward(self, x: np.ndarray, params: Dict[str, np.ndarray]) -> Tuple[np.ndarray, List[np.ndarray]]:
        h = x
        acts: List[np.ndarray] = [h]
        keys = sorted([k for k in params if k.startswith('W')], key=lambda k: int(k[1:]))
        for wk in keys:
            bk = f'b{int(wk[1:])}'
            h = h @ params[wk] + params[bk]
            if wk != keys[-1]:
                h = self._relu(h)
            acts.append(h)
        return h, acts

    def load_base(self, model_state: Dict[str, np.ndarray]) -> None:
        self.base_params = {k: np.array(v) for k, v in model_state.items()}
        self.task_params = {k: v.copy() for k, v in self.base_params.items()}

    def freeze_layers(self, layer_indices: List[int]) -> None:
        self.frozen_layers = list(set(self.frozen_layers + layer_indices))

    def unfreeze_layers(self, layer_indices: List[int]) -> None:
        self.frozen_layers = [i for i in self.frozen_layers if i not in layer_indices]

    def _apply_unfreeze_schedule(self) -> None:
        schedule = self.config.unfreeze_schedule
        unfreeze_set = set()
        for step_thresh in schedule:
            if self.step_count >= step_thresh:
                unfreeze_set.update(range(self.config.num_layers))
        self.frozen_layers = [i for i in self.frozen_layers if i not in unfreeze_set]

    def adapt_domain(self, source_features: np.ndarray, target_features: np.ndarray, num_components: int = 10) -> np.ndarray:
        source_features = np.atleast_2d(source_features)
        target_features = np.atleast_2d(target_features)
        d = min(num_components, source_features.shape[1], target_features.shape[1])
        _, s_s, _ = np.linalg.svd(source_features, full_matrices=False)
        _, s_t, _ = np.linalg.svd(target_features, full_matrices=False)
        M = np.diag(s_s[:d]) @ np.diag(1.0 / (s_t[:d] + 1e-12))
        return M

    def transfer(self, x: np.ndarray, y: np.ndarray, steps: int = 10) -> Dict[str, np.ndarray]:
        lr = self.config.fine_tune_lr
        for step in range(steps):
            self.step_count += 1
            self._apply_unfreeze_schedule()
            logits, acts = self._forward(x, self.task_params)
            loss = float(np.mean((logits - y) ** 2))
            keys = sorted([k for k in self.task_params if k.startswith('W')], key=lambda k: int(k[1:]))
            grad = 2.0 * (logits - y) / x.shape[0]
            for idx in reversed(range(len(keys))):
                wk = keys[idx]
                bk = f'b{int(wk[1:])}'
                h_prev = acts[idx]
                if idx < len(keys) - 1:
                    grad = grad * self._relu_grad(acts[idx + 1])
                db = np.sum(grad, axis=0)
                dw = h_prev.T @ grad
                dh = grad @ self.task_params[wk].T
                self.task_params[wk] -= lr * dw
                self.task_params[bk] -= lr * db
                grad = dh
            self.transfer_history.append({"step": step, "loss": loss})
        return self.task_params

    def evaluate_transfer(self, x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        logits, _ = self._forward(x, self.task_params)
        loss = float(np.mean((logits - y) ** 2))
        base_logits, _ = self._forward(x, self.base_params)
        base_loss = float(np.mean((base_logits - y) ** 2))
        return {
            'transfer_loss': loss,
            'base_loss': base_loss,
            'improvement': base_loss - loss,
            'relative_improvement': (base_loss - loss) / (base_loss + 1e-12),
        }

    def get_transfer_report(self) -> Dict[str, Any]:
        return {
            'steps': len(self.transfer_history),
            'final_loss': self.transfer_history[-1]['loss'] if self.transfer_history else None,
            'initial_loss': self.transfer_history[0]['loss'] if self.transfer_history else None,
            'improvement': self.transfer_history[0]['loss'] - self.transfer_history[-1]['loss'] if len(self.transfer_history) > 1 else 0.0,
            'frozen_layers': self.frozen_layers,
            'unfreeze_schedule': self.config.unfreeze_schedule,
        }
