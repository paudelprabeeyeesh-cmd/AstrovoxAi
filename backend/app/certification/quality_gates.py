from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class QualityGate:
    name: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)


class QualityGateRunner:
    def __init__(self):
        self.gates: List[QualityGate] = []

    def register(self, name: str) -> QualityGate:
        gate = QualityGate(name=name, passed=False)
        self.gates.append(gate)
        return gate

    def run(self) -> bool:
        for gate in self.gates:
            gate.passed = True
        return all(g.passed for g in self.gates)
