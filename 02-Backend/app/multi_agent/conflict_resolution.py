from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ConflictResolution:
    def __init__(self):
        self.resolution_history: List[Dict[str, Any]] = []

    def resolve(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        strategy = self._select_strategy(conflict)
        resolution = self._apply_strategy(strategy, conflict)
        self.resolution_history.append({"conflict": conflict, "strategy": strategy, "resolution": resolution})
        return resolution

    def _select_strategy(self, conflict: Dict[str, Any]) -> str:
        severity = conflict.get("severity", "low")
        if severity == "high":
            return "human_escalation"
        if conflict.get("type") == "resource_contention":
            return "priority_based"
        return "consensus"

    def _apply_strategy(self, strategy: str, conflict: Dict[str, Any]) -> Dict[str, Any]:
        if strategy == "human_escalation":
            return {"status": "escalated", "reason": "Requires human decision"}
        if strategy == "priority_based":
            candidates = conflict.get("candidates", [])
            best = max(candidates, key=lambda c: c.get("priority", 0)) if candidates else None
            return {"status": "resolved", "winner": best}
        if strategy == "consensus":
            candidates = conflict.get("candidates", [])
            return {"status": "resolved", "winner": candidates[0] if candidates else None}
        return {"status": "unresolved"}
