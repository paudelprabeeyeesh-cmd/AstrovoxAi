from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class MoralPrinciple:
    name: str
    description: str
    weight: float
    priority: float = 0.5
    category: str = "general"


@dataclass
class EthicalState:
    action: str
    principles_applied: List[str]
    moral_score: float
    recommendation: str
    value_conflicts: List[tuple]


class EthicalReasoner:
    def __init__(self):
        self.principles: List[MoralPrinciple] = [
            MoralPrinciple("beneficence", "Do good", weight=1.2, priority=0.8),
            MoralPrinciple("non_maleficence", "Do no harm", weight=1.5, priority=0.9),
            MoralPrinciple("autonomy", "Respect autonomy", weight=1.0, priority=0.7),
            MoralPrinciple("justice", "Treat fairly", weight=1.0, priority=0.8),
            MoralPrinciple("transparency", "Be transparent", weight=0.8, priority=0.6),
        ]
        self.judgment_history: List[EthicalState] = []

    def evaluate(self, action: str, stakeholders: List[str]) -> EthicalState:
        action_lower = action.lower()
        applied = []
        scores = {}
        for p in self.principles:
            score = self._apply_principle(p, action_lower, stakeholders)
            scores[p.name] = score
            if score > 0.3:
                applied.append(p.name)
        moral_score = float(np.mean(list(scores.values()))) if scores else 0.0
        conflicts = self._detect_conflicts(scores)
        rec = self._recommend(moral_score, conflicts)
        state = EthicalState(action=action, principles_applied=applied, moral_score=moral_score, recommendation=rec, value_conflicts=conflicts)
        self.judgment_history.append(state)
        return state

    def _apply_principle(self, principle: MoralPrinciple, action_lower: str, stakeholders: List[str]) -> float:
        keywords = principle.name.split("_") + principle.description.lower().split()
        matches = sum(action_lower.count(k) for k in keywords)
        base = 0.2 + min(matches * 0.15, 0.6)
        stake_factor = min(len(stakeholders) * 0.05, 0.2)
        return max(0.0, min(1.0, (base + stake_factor) * principle.weight))

    def _detect_conflicts(self, scores: Dict[str, float]) -> List[tuple]:
        conflicts = []
        keys = list(scores.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                diff = abs(scores[keys[i]] - scores[keys[j]])
                if diff > 0.4:
                    conflicts.append((keys[i], keys[j], diff))
        return conflicts

    def _recommend(self, moral_score: float, conflicts: List[tuple]) -> str:
        if moral_score < 0.3 or len(conflicts) > 2:
            return "Do not proceed"
        if moral_score < 0.5 or len(conflicts) > 0:
            return "Proceed with caution"
        return "Proceed as planned"

    def moral_judgment(self, action: str, stakeholders: List[str]) -> Dict[str, float]:
        state = self.evaluate(action, stakeholders)
        return {"moral_score": state.moral_score, "conflict_severity": float(np.mean([c[2] for c in state.value_conflicts])) if state.value_conflicts else 0.0, "principles_applied_count": float(len(state.principles_applied))}
