import math
import random
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class TeacherConfig:
    input_dim: int = 4
    hidden_dim: int = 8
    output_dim: int = 2


class _SimpleMatrix:
    def __init__(self, rows: int, cols: int, data: List[List[float]]):
        self.rows = rows
        self.cols = cols
        self.data = data

    @staticmethod
    def zeros(rows: int, cols: int) -> "_SimpleMatrix":
        return _SimpleMatrix(rows, cols, [[0.0] * cols for _ in range(rows)])

    @staticmethod
    def randn(rows: int, cols: int) -> "_SimpleMatrix":
        return _SimpleMatrix(rows, cols, [[random.gauss(0, 0.1) for _ in range(cols)] for _ in range(rows)])

    def __matmul__(self, other: "_SimpleMatrix") -> "_SimpleMatrix":
        assert self.cols == other.rows
        result = _SimpleMatrix.zeros(self.rows, other.cols)
        for i in range(self.rows):
            for j in range(other.cols):
                s = 0.0
                for k in range(self.cols):
                    s += self.data[i][k] * other.data[k][j]
                result.data[i][j] = s
        return result

    def relu(self) -> "_SimpleMatrix":
        result = _SimpleMatrix.zeros(self.rows, self.cols)
        for i in range(self.rows):
            for j in range(self.cols):
                result.data[i][j] = max(0.0, self.data[i][j])
        return result

    def add_bias(self, bias: List[float]) -> "_SimpleMatrix":
        assert len(bias) == self.cols
        result = _SimpleMatrix.zeros(self.rows, self.cols)
        for i in range(self.rows):
            for j in range(self.cols):
                result.data[i][j] = self.data[i][j] + bias[j]
        return result

    def transpose(self) -> "_SimpleMatrix":
        result = _SimpleMatrix.zeros(self.cols, self.rows)
        for i in range(self.rows):
            for j in range(self.cols):
                result.data[j][i] = self.data[i][j]
        return result


class TeacherNetwork:
    def __init__(self, config: Optional[TeacherConfig] = None):
        self.config = config or TeacherConfig()
        self.W1 = _SimpleMatrix.randn(self.config.input_dim, self.config.hidden_dim)
        self.b1 = [0.0] * self.config.hidden_dim
        self.W2 = _SimpleMatrix.randn(self.config.hidden_dim, self.config.output_dim)
        self.b2 = [0.0] * self.config.output_dim

    def forward(self, x: List[List[float]]) -> List[List[float]]:
        X = _SimpleMatrix(len(x), self.config.input_dim, x)
        h = (X @ self.W1).add_bias(self.b1).relu()
        out = (h @ self.W2).add_bias(self.b2)
        return out.data

    def get_soft_targets(self, logits: List[List[float]], temperature: float = 2.0) -> List[List[float]]:
        scaled = [[v / temperature for v in row] for row in logits]
        softmax = []
        for row in scaled:
            max_val = max(row)
            exps = [math.exp(v - max_val) for v in row]
            total = sum(exps)
            softmax.append([e / total for e in exps])
        return softmax
