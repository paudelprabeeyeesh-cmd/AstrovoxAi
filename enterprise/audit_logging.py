"""
Audit logging for AstrovoxAI.
Provides tamper-evident audit trails for enterprise compliance.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    CONFIGURATION_CHANGE = "configuration_change"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    USER_INVITED = "user_invited"
    USER_REMOVED = "user_removed"
    BILLING_EVENT = "billing_event"


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    event_id: str
    actor_id: Optional[str]
    actor_type: str
    event_type: AuditEventType
    resource_type: str
    resource_id: Optional[str]
    action: str
    result: str
    severity: AuditSeverity
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    hash_chain: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "event_type": self.event_type.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "result": self.result,
            "severity": self.severity.value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "hash_chain": self.hash_chain,
        }


@dataclass
class AuditLogQuery:
    actor_id: Optional[str] = None
    event_type: Optional[AuditEventType] = None
    resource_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    severity: Optional[AuditSeverity] = None
    limit: int = 100
    offset: int = 0


class AuditLogger:
    """Provides tamper-evident audit logging."""

    def __init__(self, storage_backend: Optional[Any] = None):
        self._storage = storage_backend
        self._events: List[AuditEvent] = []
        self._hash_chain: Optional[str] = None

    def log_event(
        self,
        actor_id: Optional[str],
        actor_type: str,
        event_type: AuditEventType,
        resource_type: str,
        action: str,
        result: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            actor_id=actor_id,
            actor_type=actor_type,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )
        event.hash_chain = self._compute_hash(event)
        self._events.append(event)
        logger.debug("Logged audit event %s", event.event_id)
        return event

    def query(self, query: AuditLogQuery) -> List[AuditEvent]:
        results = self._events
        if query.actor_id:
            results = [e for e in results if e.actor_id == query.actor_id]
        if query.event_type:
            results = [e for e in results if e.event_type == query.event_type]
        if query.resource_type:
            results = [e for e in results if e.resource_type == query.resource_type]
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]
        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]
        if query.severity:
            results = [e for e in results if e.severity == query.severity]
        return results[query.offset:query.offset + query.limit]

    def _compute_hash(self, event: AuditEvent) -> str:
        import hashlib
        data = f"{event.event_id}:{event.timestamp.isoformat()}:{event.action}"
        if self._hash_chain:
            data += f":{self._hash_chain}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        for i, event in enumerate(self._events):
            if event.hash_chain != self._compute_hash(event):
                return False
        return True
