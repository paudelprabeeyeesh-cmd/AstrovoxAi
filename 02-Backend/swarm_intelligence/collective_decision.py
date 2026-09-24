import numpy as np
from typing import List, Dict, Tuple, Optional


class CollectiveAgent:
    def __init__(self, agent_id: int, options: List[str], seed: Optional[int] = None):
        self.agent_id = agent_id
        self.options = options
        self.preferences: Dict[str, float] = {opt: 0.0 for opt in options}
        self.confidence: Dict[str, float] = {opt: 0.0 for opt in options}
        self.rng = np.random.default_rng(seed)

    def initial_preferences(self) -> None:
        raw = self.rng.dirichlet(np.ones(len(self.options)))
        for opt, val in zip(self.options, raw):
            self.preferences[opt] = float(val)
            self.confidence[opt] = float(self.rng.uniform(0.3, 1.0))

    def update_preferences(self, social_influence: Dict[str, float], alpha: float = 0.3) -> None:
        for opt in self.options:
            self.preferences[opt] = (1 - alpha) * self.preferences[opt] + alpha * social_influence.get(opt, 0.0)
            total = sum(self.preferences.values())
            if total > 0:
                self.preferences[opt] /= total
            self.confidence[opt] = min(1.0, self.confidence[opt] + 0.05)

    def choose(self) -> str:
        opts = list(self.preferences.keys())
        vals = np.array([self.preferences[o] for o in opts], dtype=float)
        if vals.sum() == 0:
            return self.rng.choice(opts)
        return str(opts[int(np.argmax(vals))])

    def estimate_quality(self, choice: str) -> float:
        return float(self.preferences[choice] * self.confidence[choice])


class CollectiveDecision:
    def __init__(self, n_agents: int, options: List[str], seed: Optional[int] = None):
        self.agents = [CollectiveAgent(i, options, seed=seed) for i in range(n_agents)]
        self.options = options
        self.decision_history: List[str] = []
        self.convergence_history: List[float] = []

    def initialize(self) -> None:
        for agent in self.agents:
            agent.initial_preferences()

    def round(self, alpha: float = 0.3) -> Dict[str, float]:
        votes: Dict[str, float] = {opt: 0.0 for opt in self.options}
        for agent in self.agents:
            choice = agent.choose()
            quality = agent.estimate_quality(choice)
            votes[choice] += quality
        total = sum(votes.values())
        if total > 0:
            votes = {k: v / total for k, v in votes.items()}
        for agent in self.agents:
            agent.update_preferences(votes, alpha=alpha)
        best = max(votes, key=lambda k: votes[k])
        self.decision_history.append(best)
        entropy = -sum(v * np.log(v + 1e-12) for v in votes.values())
        self.convergence_history.append(entropy)
        return votes

    def decide(self, n_rounds: int = 10, alpha: float = 0.3) -> Tuple[str, List[str], List[float]]:
        self.initialize()
        for _ in range(n_rounds):
            self.round(alpha=alpha)
        votes = self._current_votes()
        decision = max(votes, key=lambda k: votes[k])
        return decision, self.decision_history, self.convergence_history

    def _current_votes(self) -> Dict[str, float]:
        votes: Dict[str, float] = {opt: 0.0 for opt in self.options}
        for agent in self.agents:
            choice = agent.choose()
            votes[choice] += agent.estimate_quality(choice)
        total = sum(votes.values())
        if total > 0:
            votes = {k: v / total for k, v in votes.items()}
        return votes
