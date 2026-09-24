from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class Scenario:
    id: str
    initial_state: Dict[str, Any]
    actions: List[Dict[str, Any]]
    outcomes: Dict[str, Any] = field(default_factory=dict)
    probability: float = 1.0


class SimulationEngine:
    def __init__(self, random_seed: Optional[int] = None):
        self.rng = np.random.default_rng(random_seed)
        self.scenarios: List[Scenario] = []

    def generate_scenarios(self, initial_state: Dict[str, Any], n: int = 10) -> List[Scenario]:
        scenarios = []
        for i in range(n):
            actions = self._random_actions(i)
            scenario = Scenario(id=f"scenario_{i}", initial_state=initial_state.copy(), actions=actions)
            scenarios.append(scenario)
        self.scenarios.extend(scenarios)
        return scenarios

    def run_monte_carlo(self, state: Dict[str, Any], horizon: int = 5, samples: int = 100) -> Dict[str, Any]:
        outcomes = []
        for _ in range(samples):
            trajectory = self._simulate_trajectory(state, horizon)
            outcomes.append(trajectory)
        values = np.array([t[-1].get("value", 0.0) for t in outcomes])
        return {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "samples": samples,
        }

    def _random_actions(self, seed: int) -> List[Dict[str, Any]]:
        local_rng = np.random.default_rng(seed)
        actions = []
        for _ in range(5):
            actions.append({
                "type": local_rng.choice(["move", "interact", "wait"]),
                "magnitude": float(local_rng.uniform(0.0, 1.0)),
            })
        return actions

    def _simulate_trajectory(self, state: Dict[str, Any], horizon: int) -> List[Dict[str, Any]]:
        trajectory = [state.copy()]
        current = state.copy()
        for _ in range(horizon):
            current = current.copy()
            current["value"] = current.get("value", 0.0) + self.rng.normal(0, 0.1)
            trajectory.append(current)
        return trajectory

    def evaluate_scenario(self, scenario: Scenario) -> Dict[str, float]:
        value = 0.0
        for action in scenario.actions:
            value += action.get("magnitude", 0.0) * (1.0 if action.get("type") == "interact" else 0.1)
        scenario.outcomes = {"value": value}
        return scenario.outcomes

    def top_scenarios(self, n: int = 5) -> List[Scenario]:
        scored = [(s, s.outcomes.get("value", 0.0)) for s in self.scenarios]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:n]]
