import numpy as np
from typing import List, Dict, Tuple, Optional


class HumanSwarmAgent:
    def __init__(self, agent_id: int, seed: Optional[int] = None):
        self.agent_id = agent_id
        self.rng = np.random.default_rng(seed)
        self.estimate: float = 0.0
        self.confidence: float = 0.0
        self.history: List[float] = []

    def initial_estimate(self, low: float, high: float) -> None:
        self.estimate = self.rng.uniform(low, high)
        self.confidence = self.rng.uniform(0.2, 1.0)

    def deliberate(self, swarm_mean: float, swarm_std: float, alpha: float = 0.3) -> None:
        if swarm_std > 1e-6:
            z = (swarm_mean - self.estimate) / swarm_std
        else:
            z = 0.0
        adjustment = alpha * np.tanh(z)
        self.estimate += adjustment
        self.confidence = min(1.0, self.confidence + 0.02)
        self.history.append(self.estimate)

    def weighted_contribution(self) -> Tuple[float, float]:
        return self.estimate, self.confidence


class HumanSwarmIntelligence:
    def __init__(self, n_agents: int, seed: Optional[int] = None):
        self.agents = [HumanSwarmAgent(i, seed=seed) for i in range(n_agents)]
        self.convergence_history: List[float] = []

    def initialize(self, low: float, high: float) -> None:
        for agent in self.agents:
            agent.initial_estimate(low, high)

    def round(self, alpha: float = 0.3) -> Tuple[float, float]:
        estimates = np.array([a.estimate for a in self.agents])
        confidences = np.array([a.confidence for a in self.agents])
        swarm_mean = float(np.average(estimates, weights=confidences))
        swarm_std = float(np.sqrt(np.average((estimates - swarm_mean) ** 2, weights=confidences)))
        for agent in self.agents:
            agent.deliberate(swarm_mean, swarm_std, alpha=alpha)
        self.convergence_history.append(swarm_std)
        return swarm_mean, swarm_std

    def predict(self, n_rounds: int = 10, alpha: float = 0.3) -> Tuple[float, List[float], List[float]]:
        self.initialize(0.0, 100.0)
        for _ in range(n_rounds):
            self.round(alpha=alpha)
        estimates = np.array([a.estimate for a in self.agents])
        confidences = np.array([a.confidence for a in self.agents])
        final = float(np.average(estimates, weights=confidences))
        return final, estimates.tolist(), self.convergence_history
