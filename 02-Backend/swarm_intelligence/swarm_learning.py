import numpy as np
from typing import List, Dict, Tuple, Optional


class SwarmNode:
    def __init__(self, node_id: int, input_dim: int, seed: Optional[int] = None):
        self.node_id = node_id
        self.rng = np.random.default_rng(seed)
        self.weights = self.rng.normal(0, 0.1, size=input_dim)
        self.local_history: List[float] = []
        self.knowledge: np.ndarray = self.weights.copy()

    def local_train(self, X: np.ndarray, y: np.ndarray, lr: float = 0.01, epochs: int = 5) -> float:
        loss_history = []
        for _ in range(epochs):
            preds = X @ self.weights
            errors = preds - y
            grad = X.T @ errors / len(y)
            self.weights -= lr * grad
            mse = float(np.mean(errors ** 2))
            loss_history.append(mse)
        self.knowledge = self.weights.copy()
        self.local_history.extend(loss_history)
        return float(np.mean(loss_history))

    def update_from_swarm(self, aggregated: np.ndarray, alpha: float = 0.5) -> None:
        self.weights = (1 - alpha) * self.weights + alpha * aggregated
        self.knowledge = self.weights.copy()


class SwarmLearning:
    def __init__(self, n_nodes: int, input_dim: int, seed: Optional[int] = None):
        self.nodes = [SwarmNode(i, input_dim, seed=seed) for i in range(n_nodes)]
        self.global_knowledge: Optional[np.ndarray] = None
        self.round_losses: List[float] = []

    def round(self, X: np.ndarray, y: np.ndarray, lr: float = 0.01, epochs: int = 5, alpha: float = 0.5) -> float:
        local_losses = []
        for node in self.nodes:
            loss = node.local_train(X, y, lr=lr, epochs=epochs)
            local_losses.append(loss)
        weights = np.vstack([node.knowledge for node in self.nodes])
        aggregated = np.mean(weights, axis=0)
        self.global_knowledge = aggregated.copy()
        for node in self.nodes:
            node.update_from_swarm(aggregated, alpha=alpha)
        avg_loss = float(np.mean(local_losses))
        self.round_losses.append(avg_loss)
        return avg_loss

    def train(self, X: np.ndarray, y: np.ndarray, rounds: int = 10, lr: float = 0.01, epochs: int = 5, alpha: float = 0.5) -> List[float]:
        for _ in range(rounds):
            self.round(X, y, lr=lr, epochs=epochs, alpha=alpha)
        return self.round_losses

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.global_knowledge is None:
            raise RuntimeError("Swarm not trained")
        return X @ self.global_knowledge
