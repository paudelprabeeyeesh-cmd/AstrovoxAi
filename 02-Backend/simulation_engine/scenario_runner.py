import copy
import dataclasses
from typing import Any, Dict, List

from simulation_engine.simulator import Simulator


@dataclasses.dataclass
class Scenario:
    id: str
    initial_state: Dict[str, Any]
    actions: List[Dict[str, Any]]


class ScenarioRunner:
    def __init__(self, seed: int = 0):
        self.simulator = Simulator(seed=seed)

    def execute_actions(self, state: Dict[str, Any], actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.simulator.simulate_step(state, actions)

    def run_scenario(self, scenario: Scenario, horizon: int = 1) -> Dict[str, Any]:
        current = copy.deepcopy(scenario.initial_state)
        for _ in range(horizon):
            current = self.execute_actions(current, scenario.actions)
        return current

    def run_scenario_trajectory(self, scenario: Scenario, horizon: int = 1) -> List[Dict[str, Any]]:
        return self.simulator.run_trajectory(scenario.initial_state, scenario.actions, horizon)
