import numpy as np
from typing import Any, Callable, Dict, List, Optional


class Agent:
    def __init__(self, name: str):
        self.name = name
        self.arguments: List[np.ndarray] = []
        self.critiques: List[str] = []

    def propose(self, argument: np.ndarray) -> None:
        self.arguments.append(np.array(argument, copy=True))

    def critique(self, target: "Agent", text: str) -> None:
        target.critiques.append(text)


class DebateOrchestrator:
    def __init__(self, convergence_threshold: float = 1e-4, max_rounds: int = 50):
        self.agents: Dict[str, Agent] = {}
        self.rounds: int = 0
        self.converged: bool = False
        self.convergence_threshold = convergence_threshold
        self.max_rounds = max_rounds
        self.history: List[Dict[str, np.ndarray]] = []

    def register(self, agent: Agent) -> None:
        self.agents[agent.name] = agent

    def _mean_argument(self) -> Optional[np.ndarray]:
        valid = [a for a in self.agents.values() if a.arguments]
        if not valid:
            return None
        return np.mean([a.arguments[-1] for a in valid], axis=0)

    def detect_convergence(self) -> bool:
        if len(self.history) < 2:
            return False
        prev = np.array([self.history[-2][name] for name in self.agents], dtype=float)
        curr = np.array([self.history[-1][name] for name in self.agents], dtype=float)
        delta = np.linalg.norm(curr - prev)
        return delta < self.convergence_threshold

    def run_round(self) -> bool:
        snapshot = {}
        for name, agent in self.agents.items():
            if agent.arguments:
                snapshot[name] = agent.arguments[-1]
        self.history.append(snapshot)
        self.rounds += 1
        self.converged = self.detect_convergence()
        return self.converged or self.rounds >= self.max_rounds

    def run_debate(self) -> Dict[str, Any]:
        self.rounds = 0
        self.converged = False
        self.history = []
        done = False
        while not done:
            done = self.run_round()
        return {
            "rounds": self.rounds,
            "converged": self.converged,
            "final_state": {
                name: (agent.arguments[-1].tolist() if agent.arguments else None)
                for name, agent in self.agents.items()
            },
        }
