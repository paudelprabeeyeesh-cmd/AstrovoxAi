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


class SecurityOrchestrator:
    def __init__(self) -> None:
        self._playbooks: Dict[str, Playbook] = {}
        self._audit: List[Dict[str, Any]] = []
        self._key = hashlib.sha256(b"orchestrator").digest()

    def add_playbook(self, playbook: Playbook) -> None:
        self._playbooks[playbook.id] = playbook

    def incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        incident["detected_at"] = time.time()
        resolution = self._resolve(incident)
        result = {"incident": incident, "resolution": resolution, "status": "closed"}
        self._audit.append(result)
        return result

    def _resolve(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        tags = incident.get("tags", [])
        candidates = [pb for pb in self._playbooks.values() if any(t in pb.tags for t in tags)]
        for pb in candidates:
            if self._match(pb, incident):
                return self._run(pb, incident)
        return {"status": "escalated", "reason": "no_playbook"}

    @staticmethod
    def _match(pb: Playbook, incident: Dict[str, Any]) -> bool:
        return incident.get("severity", 0) >= pb.threshold

    def _run(self, pb: Playbook, incident: Dict[str, Any]) -> Dict[str, Any]:
        outputs = {}
        for step in pb.steps:
            action = step.get("action")
            if action == "log":
                outputs[step.get("name", "log")] = incident
            elif action == "block":
                outputs[step.get("name", "block")] = incident.get("source", "unknown")
            elif action == "remediate":
                outputs[step.get("name", "remediate")] = incident
        return {"playbook": pb.id, "outputs": outputs, "status": "resolved"}

    def evaluate_control(self, control: Dict[str, Any]) -> Dict[str, Any]:
        sensitivity = control.get("sensitivity", "medium")
        mappings = {"critical": "automated", "high": "automated", "medium": "manual", "low": "log"}
        source = mappings.get(sensitivity, "manual")
        if source == "automated":
            result = self.incident(control)
        else:
            result = {"incident": control, "resolution": {"status": "logged"}, "status": "open"}
        self._audit.append(result)
        return result

    def policy_context(self, subject: str, resource: str) -> Dict[str, Any]:
        h = hashlib.sha256((subject + resource).encode()).hexdigest()
        return {"subject": subject, "resource": resource, "session": h[:16]}

    def audit_chain(self, signature: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._audit

    def validate_playbook(self, pb: Playbook) -> bool:
        if not pb.steps:
            return False
        return True


class SplunkIntegration:
    @staticmethod
    def transform(incidents: List[Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"sourcetype": "orchestrator", "raw": json.dumps(i)} for i in incidents]


class SOARIntegration:
    def __init__(self, orchestrator: SecurityOrchestrator) -> None:
        self._orchestrator = orchestrator

    def trigger(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        return self._orchestrator.incident(incident)
