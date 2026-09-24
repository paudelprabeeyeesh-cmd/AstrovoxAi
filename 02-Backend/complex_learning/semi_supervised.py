import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


class SemiSupervisedLearner:
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_classes: int = 5,
                 lr: float = 0.01, temperature: float = 1.0, ema_decay: float = 0.999):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.lr = lr
        self.temperature = temperature
        self.ema_decay = ema_decay
        self.params: Dict[str, np.ndarray] = {}
        self.ema_params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self.supervised_losses: List[float] = []
        self.unsupervised_losses: List[float] = []
        self.pseudo_labels: List[np.ndarray] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        self.params["W1"] = np.random.randn(self.input_dim, self.hidden_dim).astype(np.float64) * 0.1
        self.params["b1"] = np.zeros(self.hidden_dim, dtype=np.float64)
        self.params["W2"] = np.random.randn(self.hidden_dim, self.num_classes).astype(np.float64) * 0.1
        self.params["b2"] = np.zeros(self.num_classes, dtype=np.float64)
        self.ema_params = {k: v.copy() for k, v in self.params.items()}

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _forward(self, x: np.ndarray, params: Dict[str, np.ndarray]) -> np.ndarray:
        h = self._relu(x @ params["W1"] + params["b1"])
        return h @ params["W2"] + params["b2"]

    def _compute_loss(self, logits: np.ndarray, y: np.ndarray) -> float:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        return float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

    def _ema_update(self) -> None:
        for k in self.params:
            self.ema_params[k] = self.ema_decay * self.ema_params[k] + (1.0 - self.ema_decay) * self.params[k]

    def supervised_train_step(self, x: np.ndarray, y: np.ndarray, lr: Optional[float] = None) -> float:
        lr = lr if lr is not None else self.lr
        logits = self._forward(x, self.params)
        loss = self._compute_loss(logits, y)
        self.loss_history.append(loss)
        self.supervised_losses.append(loss)
        probs = self._softmax(logits)
        y_int = y.astype(int)
        grad = probs.copy()
        grad[np.arange(len(y_int)), y_int] -= 1
        grad /= len(y_int)
        h = self._relu(x @ self.params["W1"] + self.params["b1"])
        dW2 = h.T @ grad
        db2 = np.sum(grad, axis=0)
        dh = grad @ self.params["W2"].T
        dh = dh * (h > 0)
        dW1 = x.T @ dh
        db1 = np.sum(dh, axis=0)
        self.params["W1"] -= lr * dW1
        self.params["b1"] -= lr * db1
        self.params["W2"] -= lr * dW2
        self.params["b2"] -= lr * db2
        self._ema_update()
        return loss

    def generate_pseudo_labels(self, unlabeled_x: np.ndarray, threshold: float = 0.95) -> Tuple[np.ndarray, np.ndarray]:
        logits = self._forward(unlabeled_x, self.ema_params)
        probs = self._softmax(logits)
        max_probs = np.max(probs, axis=1)
        pseudo_y = np.argmax(probs, axis=1)
        mask = max_probs >= threshold
        if not np.any(mask):
            return np.empty((0, unlabeled_x.shape[1])), np.empty((0,), dtype=int)
        self.pseudo_labels.append(pseudo_y[mask])
        return unlabeled_x[mask], pseudo_y[mask]

    def consistency_loss(self, x: np.ndarray, x_aug: np.ndarray) -> float:
        logits1 = self._forward(x, self.params)
        logits2 = self._forward(x_aug, self.ema_params)
        probs1 = self._softmax(logits1)
        probs2 = self._softmax(logits2)
        return float(np.mean(np.sum((probs1 - probs2) ** 2, axis=1)))

    def train_step_semi(self, labeled_x: np.ndarray, labeled_y: np.ndarray,
                        unlabeled_x: np.ndarray, unlabeled_x_aug: np.ndarray,
                        lambda_u: float = 1.0, lr: Optional[float] = None) -> Dict[str, float]:
        lr = lr if lr is not None else self.lr
        logits = self._forward(labeled_x, self.params)
        loss_s = self._compute_loss(logits, labeled_y)
        cons_loss = self.consistency_loss(unlabeled_x, unlabeled_x_aug)
        loss = loss_s + lambda_u * cons_loss
        self.loss_history.append(loss)
        self.supervised_losses.append(loss_s)
        self.unsupervised_losses.append(cons_loss)
        probs = self._softmax(logits)
        y_int = labeled_y.astype(int)
        grad = probs.copy()
        grad[np.arange(len(y_int)), y_int] -= 1
        grad /= len(y_int)
        h = self._relu(labeled_x @ self.params["W1"] + self.params["b1"])
        dW2 = h.T @ grad
        db2 = np.sum(grad, axis=0)
        dh = grad @ self.params["W2"].T
        dh = dh * (h > 0)
        dW1 = labeled_x.T @ dh
        db1 = np.sum(dh, axis=0)
        logits_u1 = self._forward(unlabeled_x, self.params)
        probs_u1 = self._softmax(logits_u1)
        logits_u2 = self._forward(unlabeled_x_aug, self.ema_params)
        probs_u2 = self._softmax(logits_u2)
        grad_u = (probs_u1 - probs_u2) * 2 / len(unlabeled_x)
        dh_u = grad_u @ self.params["W2"].T
        h_u = self._relu(unlabeled_x @ self.params["W1"] + self.params["b1"])
        dW2 += h_u.T @ grad_u
        db2 += np.sum(grad_u, axis=0)
        dW1 += unlabeled_x.T @ dh_u
        db1 += np.sum(dh_u, axis=0)
        self.params["W1"] -= lr * dW1
        self.params["b1"] -= lr * db1
        self.params["W2"] -= lr * dW2
        self.params["b2"] -= lr * db2
        self._ema_update()
        return {"loss": float(loss), "supervised": float(loss_s), "unsupervised": float(cons_loss)}

    def get_semi_sup_report(self) -> Dict[str, Any]:
        return {
            "total_steps": len(self.loss_history),
            "supervised_steps": len(self.supervised_losses),
            "unsupervised_steps": len(self.unsupervised_losses),
            "last_loss": float(self.loss_history[-1]) if self.loss_history else None,
            "mean_supervised": float(np.mean(self.supervised_losses[-10:])) if self.supervised_losses else None,
            "pseudo_label_generations": len(self.pseudo_labels),
        }
