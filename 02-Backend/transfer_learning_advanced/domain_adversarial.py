import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class DomainAlg(Enum):
    DANN = "dann"
    CDAN = "cdan"
    JAN = "jan"


@dataclass
class DANNMetrics:
    epoch: int = 0
    classification_loss: float = 0.0
    domain_loss: float = 0.0
    total_loss: float = 0.0
    domain_accuracy: float = 0.0


class GradientReversal:
    def __init__(self, lambda_val: float = 1.0):
        self.lambda_val = lambda_val

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return x

    def backward(self, grad: np.ndarray) -> np.ndarray:
        return -self.lambda_val * grad


class DomainClassifier:
    def __init__(self, input_dim: int, hidden_dim: int = 32):
        self.W = np.random.randn(input_dim, hidden_dim).astype(np.float64) * 0.1
        self.b = np.zeros(hidden_dim, dtype=np.float64)
        self.W_out = np.random.randn(hidden_dim, 1).astype(np.float64) * 0.1
        self.b_out = np.zeros(1, dtype=np.float64)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def forward(self, x: np.ndarray) -> np.ndarray:
        h = self._relu(x @ self.W + self.b)
        logits = h @ self.W_out + self.b_out
        return logits

    def compute_loss(self, x: np.ndarray, domain_labels: np.ndarray) -> Tuple[float, np.ndarray]:
        logits = self.forward(x)
        loss = float(np.mean(np.log(1 + np.exp(-logits * domain_labels.reshape(-1, 1) * 2 - 1)))
        return loss, logits


class DomainAdversarialTrainer:
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        output_dim: int = 5,
        lambda_init: float = 1.0,
        gamma: float = 10.0
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.lambda_init = lambda_init
        self.gamma = gamma
        self.epoch = 0
        self.metrics_history: List[DANNMetrics] = []
        self._init_params()

    def _init_params(self) -> None:
        self.W_shared = np.random.randn(self.input_dim, self.hidden_dim).astype(np.float64) * 0.1
        self.b_shared = np.zeros(self.hidden_dim, dtype=np.float64)
        self.W_cls = np.random.randn(self.hidden_dim, self.output_dim).astype(np.float64) * 0.1
        self.b_cls = np.zeros(self.output_dim, dtype=np.float64)
        self.domain_clf = DomainClassifier(self.hidden_dim)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        h = self._relu(x @ self.W_shared + self.b_shared)
        logits = h @ self.W_cls + self.b_cls
        return h, logits

    def _compute_grl_lambda(self) -> float:
        p = 2.0 / (1.0 + np.exp(-self.gamma * self.epoch / 100.0)) - 1.0
        return self.lambda_init * p

    def train_step(
        self,
        source_x: np.ndarray,
        source_y: np.ndarray,
        target_x: np.ndarray,
        lr: float = 0.01
    ) -> DANNMetrics:
        self.epoch += 1
        lambda_grl = self._compute_grl_lambda()
        n_src = len(source_x)
        n_tgt = len(target_x)
        x_all = np.vstack([source_x, target_x])
        domain_labels = np.concatenate([
            np.ones(n_src, dtype=np.float64),
            -np.ones(n_tgt, dtype=np.float64)
        ])

        h, logits_cls = self._forward(source_x)
        probs = self._softmax(logits_cls)
        y_int = source_y.astype(int)
        cls_loss = float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

        h_all, _ = self._forward(x_all)
        domain_loss, domain_logits = self.domain_clf.compute_loss(h_all, domain_labels)
        total_loss = cls_loss + lambda_grl * domain_loss

        grad = probs.copy()
        grad[np.arange(len(y_int)), y_int] -= 1
        grad /= len(y_int)
        dW_cls = h.T @ grad
        db_cls = np.sum(grad, axis=0)
        dh_cls = grad @ self.W_cls.T
        dh_cls = dh_cls * (h > 0)
        dW_shared_cls = source_x.T @ dh_cls
        db_shared_cls = np.sum(dh_cls, axis=0)
        self.W_cls -= lr * dW_cls
        self.b_cls -= lr * db_cls
        self.W_shared -= lr * dW_shared_cls
        self.b_shared -= lr * db_shared_cls

        domain_preds = (domain_logits.ravel() > 0).astype(int)
        domain_acc = float(np.mean(domain_preds == ((domain_labels > 0).astype(int))))

        metrics = DANNMetrics(
            epoch=self.epoch,
            classification_loss=cls_loss,
            domain_loss=domain_loss,
            total_loss=total_loss,
            domain_accuracy=domain_acc
        )
        self.metrics_history.append(metrics)
        return metrics

    def adapt(
        self,
        target_x: np.ndarray,
        epochs: int = 5,
        lr: float = 0.01
    ) -> List[DANNMetrics]:
        metrics_list = []
        dummy_y = np.zeros(len(target_x), dtype=int)
        for _ in range(epochs):
            metrics = self.train_step(target_x, dummy_y, target_x, lr=lr)
            metrics_list.append(metrics)
        return metrics_list

    def get_metrics_summary(self) -> Dict[str, float]:
        if not self.metrics_history:
            return {}
        last = self.metrics_history[-1]
        return {
            "classification_loss": last.classification_loss,
            "domain_loss": last.domain_loss,
            "total_loss": last.total_loss,
            "domain_accuracy": last.domain_accuracy,
            "epochs": len(self.metrics_history)
        }
