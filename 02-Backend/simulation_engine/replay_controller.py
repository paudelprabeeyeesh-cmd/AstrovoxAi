import dataclasses
import json
import time
from typing import Any, Dict, List


@dataclasses.dataclass
class ReplayRecord:
    scenario_id: str
    initial_state: Dict[str, Any]
    actions: List[Dict[str, Any]]
    seed: int
    timestamp: float


class ReplayController:
    def __init__(self, seed: int = 0):
        self._records: List[ReplayRecord] = []
        self.seed = seed

    def record(self, scenario_id: str, initial_state: Dict[str, Any], actions: List[Dict[str, Any]]) -> None:
        self._records.append(ReplayRecord(
            scenario_id=scenario_id,
            initial_state=json.loads(json.dumps(initial_state)),
            actions=json.loads(json.dumps(actions)),
            seed=self.seed,
            timestamp=time.time(),
        ))

    def get_records(self) -> List[ReplayRecord]:
        return list(self._records)

    def replay(self, simulator_cls: Any) -> List[Dict[str, Any]]:
        results = []
        for rec in self._records:
            sim = simulator_cls(seed=rec.seed)
            traj = sim.run_trajectory(rec.initial_state, rec.actions, horizon=1)
            results.append(traj[-1])
        return results
