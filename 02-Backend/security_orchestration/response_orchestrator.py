import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from security_orchestration.playbook_runner import Playbook, PlaybookRunner
from security_orchestration.policy_engine import PolicyEngine, RBACEngine


@dataclass
class SecurityIncident:
    id: str
    source: str
    event_type: str
    severity: float
    tags: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ResponseOrchestrator:
    def __init__(self) -> None:
        self._playbooks: Dict[str, Playbook] = {}
        self._incidents: List[Dict[str, Any]] = []
        self._runner = PlaybookRunner()
        self._policy = PolicyEngine()
        self._rbac = RBACEngine()
        self._key = hashlib.sha256(b"orchestrator").digest()

    def add_playbook(self, playbook: Playbook) -> None:
        self._playbooks[playbook.id] = playbook

    def incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        incident["detected_at"] = time.time()
        tags = incident.get("tags", [])
        candidates = [pb for pb in self._playbooks.values() if any(t in pb.tags for t in tags)]
        resolution = self._resolve(incident, candidates)
        result = {"incident": incident, "resolution": resolution, "status": "closed"}
        self._incidents.append(result)
        return result

    def evaluate_control(self, control: Dict[str, Any]) -> Dict[str, Any]:
        sensitivity = control.get("sensitivity", "medium")
        mappings = {"critical": "automated", "high": "automated", "medium": "manual", "low": "log"}
        source = mappings.get(sensitivity, "manual")
        if source == "automated":
            result = self.incident(control)
        else:
            result = {"incident": control, "resolution": {"status": "logged"}, "status": "open"}
        self._incidents.append(result)
        return result

    def policy_context(self, subject: str, resource: str) -> Dict[str, Any]:
        h = hashlib.sha256((subject + resource).encode()).hexdigest()
        return {"subject": subject, "resource": resource, "session": h[:16]}

    def audit_chain(self) -> List[Dict[str, Any]]:
        return list(self._incidents)

    def _resolve(self, incident: Dict[str, Any], candidates: List[Playbook]) -> Dict[str, Any]:
        for pb in candidates:
            if incident.get("severity", 0) >= pb.threshold:
                return self._runner.run(pb, incident)
        return {"status": "escalated", "reason": "no_playbook"}
