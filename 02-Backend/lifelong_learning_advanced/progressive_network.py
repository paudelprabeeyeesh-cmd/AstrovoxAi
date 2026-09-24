from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class ColumnConfig:
    input_dim: int
    hidden_dim: int
    output_dim: int
    lr: float = 0.01


class ProgressiveNetwork:
    def __init__(self, base_config: ColumnConfig) -> None:
        self.base_config = base_config
        self.columns: Dict[str, Dict[str, np.ndarray]] = {}
        self.frozen: List[str] = []
        self.task_count: int = 0
        self.loss_history: List[float] = []
        self._add_column("base")

    def _add_column(self, column_id: str) -> None:
        rng = np.random.default_rng(seed=42 + len(self.columns))
        scale1 = np.sqrt(2.0 / self.base_config.input_dim)
        scale2 = np.sqrt(2.0 / self.base_config.hidden_dim)
        w1 = rng.standard_normal((self.base_config.input_dim, self.base_config.hidden_dim)).astype(np.float64) * scale1
        b1 = np.zeros(self.base_config.hidden_dim, dtype=np.float64)
        w2 = rng.standard_normal((self.base_config.hidden_dim, self.base_config.output_dim)).astype(np.float64) * scale2
        b2 = np.zeros(self.base_config.output_dim, dtype=np.float64)
        self.columns[column_id] = {"W1": w1, "b1": b1, "W2": w2, "b2": b2}

    def add_task_column(self, task_id: str) -> str:
        self.task_count += 1
        column_id = f"task_{self.task_count}"
        self._add_column(column_id)
        for fid in list(self.columns.keys()):
            if fid != column_id:
                self.frozen.append(fid)
        return column_id

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _forward(self, x: np.ndarray, column_id: str) -> np.ndarray:
        params = self.columns[column_id]
        h = self._relu(x @ params["W1"] + params["b1"])
        return h @ params["W2"] + params["b2"]

    def learn_task(self, x: np.ndarray, y: np.ndarray, column_id: str, steps: int = 5) -> Dict[str, Any]:
        params = self.columns[column_id]
        lr = self.base_config.lr
        for _ in range(steps):
            logits = self._forward(x, column_id)
            loss = float(np.mean((logits - y) ** 2))
            grad = 2.0 * (logits - y) / x.shape[0]
            h = self._relu(x @ params["W1"] + params["b1"])
            db2 = np.sum(grad, axis=0)
            dw2 = h.T @ grad
            dh = grad @ params["W2"].T
            dh = dh * (h > 0)
            db1 = np.sum(dh, axis=0)
            dw1 = x.T @ dh
            params["W2"] -= lr * dw2
            params["b2"] -= lr * db2
            params["W1"] -= lr * dw1
            params["b1"] -= lr * db1
        self.loss_history.append(loss)
        return {"task_id": column_id, "final_loss": loss}

    def evaluate(self, x: np.ndarray, y: np.ndarray, column_id: str) -> Dict[str, Any]:
        logits = self._forward(x, column_id)
        loss = float(np.mean((logits - y) ** 2))
        return {"loss": loss, "column_id": column_id}

    def get_report(self) -> Dict[str, Any]:
        return {
            "columns": len(self.columns),
            "frozen": len(self.frozen),
            "tasks_learned": self.task_count,
            "last_loss": float(self.loss_history[-1]) if self.loss_history else None,
        }
