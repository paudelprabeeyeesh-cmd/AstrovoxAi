from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ColumnConfig:
    input_dim: int
    hidden_dim: int
    output_dim: int


class ProgressiveNetwork:
    def __init__(self, max_columns: int = 5):
        self.max_columns = max_columns
        self.columns: Dict[int, ColumnConfig] = {}
        self.column_params: Dict[int, Dict[str, List[float]]] = {}
        self.lateral_weights: Dict[int, List[float]] = {}
        self.task_to_column: Dict[int, int] = {}
        self.column_count = 0
        self.loss_history: Dict[int, List[float]] = {}

    def add_column(self, task_id: int, input_dim: int, hidden_dim: int, output_dim: int) -> int:
        if self.column_count >= self.max_columns:
            raise ValueError("Maximum columns reached")
        col_id = self.column_count
        self.columns[col_id] = ColumnConfig(input_dim, hidden_dim, output_dim)
        self.column_params[col_id] = {
            'W1': [0.0] * (input_dim * hidden_dim),
            'b1': [0.0] * hidden_dim,
            'W2': [0.0] * (hidden_dim * output_dim),
            'b2': [0.0] * output_dim,
        }
        self.lateral_weights[col_id] = []
        self.column_count += 1
        self.task_to_column[task_id] = col_id
        return col_id

    def _forward_column(
        self,
        col_id: int,
        x: List[float],
        lateral_input: Optional[List[float]] = None,
    ) -> List[float]:
        params = self.column_params[col_id]
        cfg = self.columns[col_id]
        hidden = [0.0] * cfg.hidden_dim
        for j in range(cfg.hidden_dim):
            s = params['b1'][j]
            for i in range(cfg.input_dim):
                s += params['W1'][j * cfg.input_dim + i] * x[i]
            if lateral_input:
                li = lateral_input[j] if j < len(lateral_input) else 0.0
                s += li
            hidden[j] = max(0.0, s)
        out = [0.0] * cfg.output_dim
        for j in range(cfg.output_dim):
            s = params['b2'][j]
            for i in range(cfg.hidden_dim):
                s += params['W2'][j * cfg.hidden_dim + i] * hidden[i]
            out[j] = s
        return out

    def forward(self, task_id: int, x: List[float]) -> List[float]:
        col_id = self.task_to_column[task_id]
        lateral = None
        if col_id > 0:
            prev_out = self._forward_column(col_id - 1, x)
            lateral = prev_out
        return self._forward_column(col_id, x, lateral_input=lateral)

    def train_step(self, task_id: int, x: List[float], y: List[float], lr: float = 0.01) -> float:
        col_id = self.task_to_column[task_id]
        params = self.column_params[col_id]
        cfg = self.columns[col_id]
        logits = self.forward(task_id, x)
        loss = sum((logits[i] - y[i]) ** 2 for i in range(len(y))) / len(y)
        grad = [2.0 * (logits[i] - y[i]) / len(y) for i in range(len(y))]
        hidden = [0.0] * cfg.hidden_dim
        for j in range(cfg.hidden_dim):
            s = params['b1'][j]
            for i in range(cfg.input_dim):
                s += params['W1'][j * cfg.input_dim + i] * x[i]
            hidden[j] = max(0.0, s)
        db2 = list(grad)
        dw2: List[float] = []
        for j in range(cfg.output_dim):
            for i in range(cfg.hidden_dim):
                dw2.append(hidden[i] * grad[j])
        dh = [0.0] * cfg.hidden_dim
        for i in range(cfg.hidden_dim):
            s = 0.0
            for j in range(cfg.output_dim):
                s += params['W2'][j * cfg.hidden_dim + i] * grad[j]
            dh[i] = s * (1.0 if hidden[i] > 0 else 0.0)
        db1 = list(dh)
        dw1: List[float] = []
        for j in range(cfg.hidden_dim):
            for i in range(cfg.input_dim):
                dw1.append(x[i] * dh[j])
        for idx, val in enumerate(dw2):
            params['W2'][idx] -= lr * val
        for idx, val in enumerate(db2):
            params['b2'][idx] -= lr * val
        for idx, val in enumerate(dw1):
            params['W1'][idx] -= lr * val
        for idx, val in enumerate(db1):
            params['b1'][idx] -= lr * val
        self.loss_history.setdefault(task_id, []).append(loss)
        return loss

    def get_column_params(self, task_id: int) -> Dict[str, List[float]]:
        col_id = self.task_to_column[task_id]
        return {k: list(v) for k, v in self.column_params[col_id].items()}

    def column_summary(self) -> Dict[int, Dict[str, int]]:
        summary: Dict[int, Dict[str, int]] = {}
        for col_id, cfg in self.columns.items():
            summary[col_id] = {
                "input_dim": cfg.input_dim,
                "hidden_dim": cfg.hidden_dim,
                "output_dim": cfg.output_dim,
                "task_id": next((tid for tid, cid in self.task_to_column.items() if cid == col_id), -1),
            }
        return summary
