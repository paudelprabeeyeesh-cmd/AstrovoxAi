from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class Principle:
    name: str
    description: str
    weight: float = 1.0
    category: str = "general"


@dataclass
class EthicalAnalysis:
    principles_applied: List[str]
    values_alignment: Dict[str, float]
    risk_score: float
    recommendation: str
    confidence: float = 0.0


class EthicalEngine:
    def __init__(self, principles: Optional[List[Principle]] = None):
        self.principles = principles or [
            Principle("beneficence", "Do good", weight=1.2),
            Principle("non_maleficence", "Do no harm", weight=1.5),
            Principle("autonomy", "Respect autonomy", weight=1.0),
            Principle("justice", "Treat fairly", weight=1.0),
            Principle("transparency", "Be transparent", weight=0.8),
            Principle("privacy", "Protect privacy", weight=1.1),
        ]
        self.value_alignments: Dict[str, float] = {p.name: 0.5 for p in self.principles}

    def analyze(self, action: str, stakeholders: List[str], context: str = "") -> EthicalAnalysis:
        applied = []
        alignments = {}
        for principle in self.principles:
            score = self._apply_principle(principle, action, stakeholders, context)
            alignments[principle.name] = score
            if score > 0.3:
                applied.append(principle.name)
        risk = self._compute_risk(alignments)
        recommendation = self._recommend(alignments, risk, stakeholders)
        confidence = self._confidence(alignments)
        return EthicalAnalysis(
            principles_applied=applied,
            values_alignment=alignments,
            risk_score=risk,
            recommendation=recommendation,
            confidence=confidence,
        )

    def _apply_principle(self, principle: Principle, action: str, stakeholders: List[str], context: str) -> float:
        action_lower = action.lower()
        context_lower = context.lower()
        keywords = principle.description.lower().split() + principle.name.split("_")
        matches = sum(action_lower.count(k) + context_lower.count(k) for k in keywords)
        base = 0.2 + min(matches * 0.15, 0.6)
        stake_factor = min(len(stakeholders) * 0.05, 0.2)
        return max(0.0, min(1.0, base + stake_factor)) * principle.weight

    def _compute_risk(self, alignments: Dict[str, float]) -> float:
        harm = alignments.get("non_maleficence", 1.0)
        privacy = alignments.get("privacy", 1.0)
        autonomy = alignments.get("autonomy", 1.0)
        risk = 1.0 - np.mean([harm, privacy, autonomy])
        return max(0.0, min(1.0, risk))

    def _recommend(self, alignments: Dict[str, float], risk: float, stakeholders: List[str]) -> str:
        if risk > 0.6:
            return "Do not proceed without addressing significant ethical concerns"
        if risk > 0.3:
            return "Proceed with caution and monitor closely"
        misaligned = [k for k, v in alignments.items() if v < 0.4]
        if misaligned:
            return f"Acceptable with improvements in: {', '.join(misaligned)}"
        return "Proceed as planned"

    def _confidence(self, alignments: Dict[str, float]) -> float:
        if not alignments:
            return 0.0
        values = np.array(list(alignments.values()))
        return float(1.0 - np.std(values))

    def value_conflicts(self, analysis: EthicalAnalysis) -> List[Tuple[str, str, float]]:
        conflicts = []
        keys = list(analysis.values_alignment.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                v1, v2 = analysis.values_alignment[keys[i]], analysis.values_alignment[keys[j]]
                diff = abs(v1 - v2)
                if diff > 0.4:
                    conflicts.append((keys[i], keys[j], diff))
        return conflicts

    def update_alignment(self, principle_name: str, new_value: float) -> None:
        self.value_alignments[principle_name] = max(0.0, min(1.0, new_value))
