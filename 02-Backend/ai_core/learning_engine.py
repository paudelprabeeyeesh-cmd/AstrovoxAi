import numpy as np
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Experience:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


class GradientLearner:
    def __init__(self, input_dim: int = 8, output_dim: int = 4, lr: float = 0.001):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.lr = lr
        self.weights = np.random.randn(input_dim, output_dim) * 0.01
        self.bias = np.zeros(output_dim)
        self._loss_history: List[float] = []

    def forward(self, x: np.ndarray) -> np.ndarray:
        if x.shape[-1] != self.input_dim:
            x = np.pad(x, (0, self.input_dim - x.shape[-1]))[: self.input_dim]
        return np.tanh(x @ self.weights + self.bias)

    def train_step(self, x: np.ndarray, target: np.ndarray) -> float:
        x = np.array(x, dtype=float)
        target = np.array(target, dtype=float)
        if x.shape[-1] != self.input_dim:
            x = np.pad(x, (0, self.input_dim - x.shape[-1]))[: self.input_dim]
        output = self.forward(x)
        error = target - output
        loss = float(np.mean(error ** 2))
        d_output = error * (1 - output ** 2)
        self.weights += self.lr * np.outer(x, d_output)
        self.bias += self.lr * d_output
        self._loss_history.append(loss)
        return loss

    def get_loss_history(self) -> List[float]:
        return list(self._loss_history)


class EpisodicMemory:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.memory: List[Dict[str, Any]] = []

    def store(self, experience: Dict[str, Any]) -> None:
        if len(self.memory) >= self.capacity:
            self.memory.pop(0)
        self.memory.append(experience)

    def sample(self, batch_size: int = 32) -> List[Dict[str, Any]]:
        if batch_size > len(self.memory):
            return list(self.memory)
        indices = np.random.choice(len(self.memory), size=batch_size, replace=False).tolist()
        return [self.memory[i] for i in indices]

    def replay(self, learner: GradientLearner) -> float:
        batch = self.sample()
        total_loss = 0.0
        for exp in batch:
            loss = learner.train_step(exp["state"], exp["target"])
            total_loss += loss
        return total_loss / max(len(batch), 1)


class AdaptationEngine:
    def __init__(self, adaptation_rate: float = 0.01, momentum: float = 0.9):
        self.adaptation_rate = adaptation_rate
        self.momentum = momentum
        self._velocity: Optional[np.ndarray] = None
        self._step_count = 0

    def adapt(self, gradient: np.ndarray) -> np.ndarray:
        gradient = np.array(gradient, dtype=float)
        if self._velocity is None or self._velocity.shape != gradient.shape:
            self._velocity = np.zeros_like(gradient)
        self._velocity = self.momentum * self._velocity - self.adaptation_rate * gradient
        self._step_count += 1
        return self._velocity

    def get_stats(self) -> Dict[str, Any]:
        return {
            "step_count": self._step_count,
            "adaptation_rate": self.adaptation_rate,
            "momentum": self.momentum,
        }


class LearningEngine:
    def __init__(self, input_dim: int = 8, output_dim: int = 4):
        self.learner = GradientLearner(input_dim=input_dim, output_dim=output_dim)
        self.episodic = EpisodicMemory()
        self.adapter = AdaptationEngine()
        self._metrics: Dict[str, List[float]] = {
            "loss": [],
            "reward": [],
        }

    def observe(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool) -> None:
        self.episodic.store({
            "state": np.array(state),
            "action": action,
            "reward": reward,
            "next_state": np.array(next_state),
            "done": done,
        })
        self._metrics["reward"].append(reward)

    def learn(self, batch_size: int = 16) -> float:
        batch = self.episodic.sample(batch_size)
        total_loss = 0.0
        for exp in batch:
            target = self.learner.forward(exp["next_state"]) * 0.99 + exp["reward"]
            loss = self.learner.train_step(exp["state"], target)
            total_loss += loss
        avg_loss = total_loss / max(len(batch), 1)
        self._metrics["loss"].append(avg_loss)
        return avg_loss

    def adapt(self, gradient: np.ndarray) -> np.ndarray:
        return self.adapter.adapt(gradient)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "avg_loss": float(np.mean(self._metrics["loss"])) if self._metrics["loss"] else 0.0,
            "avg_reward": float(np.mean(self._metrics["reward"])) if self._metrics["reward"] else 0.0,
            "episodes": len(self.episodic.memory),
            "learner_steps": self.learner.forward(np.zeros(self.learner.input_dim)).shape[0],
        }
