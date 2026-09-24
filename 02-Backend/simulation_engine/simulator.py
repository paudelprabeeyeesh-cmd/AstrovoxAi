import copy
import dataclasses
import random
from typing import Any, Dict, List


@dataclasses.dataclass
class SimulationState:
    state: Dict[str, Any]


class Simulator:
    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)
        self.seed = seed

    def simulate_step(self, state: Dict[str, Any], actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        next_state = copy.deepcopy(state)
        for action in actions:
            magnitude = float(action.get("magnitude", 0.0))
            action_type = action.get("type", "wait")
            if action_type == "interact":
                next_state["value"] = next_state.get("value", 0.0) + magnitude
            elif action_type == "wait":
                next_state["value"] = next_state.get("value", 0.0) - magnitude * 0.1
            else:
                next_state["value"] = next_state.get("value", 0.0) - magnitude * 0.05
        return next_state

    def run_trajectory(self, state: Dict[str, Any], actions: List[Dict[str, Any]], horizon: int) -> List[Dict[str, Any]]:
        trajectory = [copy.deepcopy(state)]
        current = copy.deepcopy(state)
        for _ in range(horizon):
            current = self.simulate_step(current, actions)
            trajectory.append(current)
        return trajectory

    def compute_outcome(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"value": state.get("value", 0.0)}

    def run_monte_carlo(self, state: Dict[str, Any], samples: int, horizon: int) -> List[float]:
        results = []
        for _ in range(samples):
            traj = self.run_trajectory(state, [], horizon)
            results.append(traj[-1].get("value", 0.0))
        return results
