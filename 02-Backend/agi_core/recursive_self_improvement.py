from dataclasses import dataclass
from typing import Dict, List
import numpy as np


@dataclass
class ImprovementProposal:
    capability: str
    description: str
    risk: float
    expected_gain: float
    confidence: float = 0.5
    status: str = "proposed"


class RecursiveSelfImprovement:
    def __init__(self):
        self.proposals: List[ImprovementProposal] = []
        self.improvement_history: List[Dict[str, float]] = []
        self.capability_levels: Dict[str, float] = {}

    def propose(self, capability: str, description: str, risk: float, expected_gain: float) -> ImprovementProposal:
        confidence = max(0.0, min(1.0, expected_gain / max(risk + 1e-6, 0.1)))
        proposal = ImprovementProposal(capability=capability, description=description, risk=risk, expected_gain=expected_gain, confidence=confidence)
        self.proposals.append(proposal)
        return proposal

    def validate(self, proposal: ImprovementProposal) -> bool:
        if proposal.risk > 0.8:
            return False
        if proposal.expected_gain < 0.2:
            return False
        if proposal.confidence < 0.3:
            return False
        return True

    def apply(self, proposal: ImprovementProposal) -> bool:
        if not self.validate(proposal):
            return False
        current = self.capability_levels.get(proposal.capability, 0.0)
        self.capability_levels[proposal.capability] = min(1.0, current + proposal.expected_gain * 0.2)
        proposal.status = "applied"
        self.improvement_history.append({"capability": proposal.capability, "gain": proposal.expected_gain * 0.2})
        return True

    def recursive_step(self) -> List[ImprovementProposal]:
        new_proposals = []
        for cap, level in self.capability_levels.items():
            if level < 0.8:
                prop = self.propose(capability=cap, description=f"Enhance {cap}", risk=0.2, expected_gain=0.1)
                new_proposals.append(prop)
        return new_proposals

    def get_capability_report(self) -> Dict[str, float]:
        if not self.capability_levels:
            return {"mean_capability": 0.0, "max_capability": 0.0}
        levels = np.array(list(self.capability_levels.values()))
        return {"mean_capability": float(np.mean(levels)), "max_capability": float(np.max(levels))}
