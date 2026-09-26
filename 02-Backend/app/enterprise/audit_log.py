from typing import Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def log(self, actor: str, action: str, resource: str, tenant_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "actor": actor,
            "action": action,
            "resource": resource,
            "tenant_id": tenant_id,
            "metadata": metadata or {},
        }
        self.entries.append(entry)
        logger.info("AUDIT: %s %s %s", actor, action, resource)
        return entry

    def query(self, actor: Optional[str] = None, action: Optional[str] = None, resource: Optional[str] = None, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        results = self.entries
        if actor:
            results = [e for e in results if e["actor"] == actor]
        if action:
            results = [e for e in results if e["action"] == action]
        if resource:
            results = [e for e in results if e["resource"] == resource]
        if tenant_id:
            results = [e for e in results if e["tenant_id"] == tenant_id]
        return results

    def export(self, format: str = "json") -> str:
        if format == "json":
            import json
            return json.dumps(self.entries, indent=2)
        return str(self.entries)
