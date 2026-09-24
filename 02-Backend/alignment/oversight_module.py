import math
from typing import Any, Dict, List


class OversightModule:
    def __init__(self, intervention_threshold: float = 0.4):
        self.intervention_threshold = max(0.0, min(1.0, intervention_threshold))
        self.audit_log: List[dict] = []
        self.intervention_log: List[dict] = []

    def compute_risk_score(self, action_attributes: Dict[str, float]) -> float:
        if not action_attributes:
            return 0.0
        return sum(action_attributes.values()) / len(action_attributes)

    def needs_intervention(self, action_attributes: Dict[str, float]) -> bool:
        return self.compute_risk_score(action_attributes) >= self.intervention_threshold

    def log_action(self, action_id: str, action_attributes: Dict[str, float], metadata: Dict[str, Any] = None) -> Dict[str, float]:
        risk = self.compute_risk_score(action_attributes)
        entry = {
            "action_id": action_id,
            "risk_score": risk,
            "intervention": self.needs_intervention(action_attributes),
            "metadata": metadata or {},
        }
        self.audit_log.append(entry)
        if self.needs_intervention(action_attributes):
            self._trigger_intervention(action_id, risk)
        return entry

    def _trigger_intervention(self, action_id: str, risk_score: float) -> None:
        self.intervention_log.append({
            "action_id": action_id,
            "risk_score": risk_score,
            "timestamp": 0.0,
        })

    def review_deviations(self, acceptable_threshold: float = 0.2) -> List[Dict]:
        deviations = []
        for entry in self.audit_log:
            if entry["risk_score"] > acceptable_threshold:
                deviations.append(entry)
        return deviations

    def audit_coverage(self) -> float:
        return 1.0 if self.audit_log else 0.0

    def intervention_effectiveness(self) -> float:
        if not self.intervention_log:
            return 1.0
        if not self.audit_log:
            return 0.0
        total_actions = len(self.audit_log)
        interventions = len(self.intervention_log)
        return 1.0 - (interventions / total_actions) if total_actions > 0 else 1.0

    def oversight_report(self) -> Dict[str, Any]:
        return {
            "total_actions": len(self.audit_log),
            "total_interventions": len(self.intervention_log),
            "risk_score": self.compute_risk_score({}) if not self.audit_log else sum(e["risk_score"] for e in self.audit_log) / len(self.audit_log),
            "intervention_effectiveness": self.intervention_effectiveness(),
            "needs_intervention": any(self.needs_intervention(a) for a in [e["risk_score"] for e in self.audit_log]) if self.audit_log else False,
        }
