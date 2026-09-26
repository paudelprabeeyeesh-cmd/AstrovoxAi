"""Audit logging for enterprise compliance."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    AUTH = "auth"
    ACCESS = "access"
    MODIFICATION = "modification"
    DELETION = "deletion"
    ADMIN = "admin"


@dataclass
class AuditEvent:
    event_id: str
    actor_id: str
    action: str
    event_type: AuditEventType
    resource: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogger:
    def __init__(self, storage_path: str = "/tmp/astrovox_audit"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def log(self, event: AuditEvent) -> None:
        entry = {
            "event_id": event.event_id,
            "actor_id": event.actor_id,
            "action": event.action,
            "event_type": event.event_type.value,
            "resource": event.resource,
            "metadata": event.metadata,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "occurred_at": event.occurred_at.isoformat(),
        }
        digest = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
        path = os.path.join(self.storage_path, f"{event.event_id}.json")
        try:
            with open(path, "w") as f:
                json.dump({"entry": entry, "checksum": digest}, f)
        except OSError:
            logger.exception("failed to write audit log")

    def query(self, actor_id: Optional[str] = None, resource: Optional[str] = None) -> List[AuditEvent]:
        results = []
        for filename in os.listdir(self.storage_path):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(self.storage_path, filename)
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                entry = data.get("entry", {})
                if actor_id and entry.get("actor_id") != actor_id:
                    continue
                if resource and entry.get("resource") != resource:
                    continue
                results.append(AuditEvent(**entry))
            except OSError:
                continue
        return results


audit_logger = AuditLogger()
