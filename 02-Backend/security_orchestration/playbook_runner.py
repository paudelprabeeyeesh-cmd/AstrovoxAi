import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Playbook:
    id: str
    name: str
    steps: List[Dict[str, Any]]
    threshold: float
    tags: List[str] = field(default_factory=list)


class PlaybookRunner:
    def __init__(self) -> None:
        self._runs: List[Dict[str, Any]] = []

    def run(self, playbook: Playbook, incident: Dict[str, Any]) -> Dict[str, Any]:
        outputs: Dict[str, Any] = {}
        errors: List[Dict[str, Any]] = []
        for step in playbook.steps:
            try:
                result = self._execute_step(step, incident)
                outputs[step.get("name", "step")] = result
            except Exception as exc:
                errors.append({"step": step.get("name", "step"), "error": str(exc)})
        entry = {
            "playbook_id": playbook.id,
            "incident": incident,
            "outputs": outputs,
            "errors": errors,
            "completed_at": time.time(),
        }
        self._runs.append(entry)
        status = "resolved" if not errors else "partial"
        return {"playbook": playbook.id, "outputs": outputs, "errors": errors, "status": status}

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._runs[-limit:]

    def _execute_step(self, step: Dict[str, Any], incident: Dict[str, Any]) -> Any:
        action = step.get("action")
        if action == "log":
            return incident
        if action == "block":
            return incident.get("source", "unknown")
        if action == "remediate":
            return incident
        if action == "notify":
            return {"notified": True, "message": step.get("message", "")}
        if action == "escalate":
            raise RuntimeError("escalate")
        return None
