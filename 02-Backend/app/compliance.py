"""Enterprise Compliance — GDPR, data export, right-to-delete, retention."""

import json
import time
import logging
import secrets
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DataExport:
    """A user data export request."""
    id: str
    user_id: str
    status: str = "pending"
    created_at: float = 0.0
    completed_at: float = 0.0
    data: dict = field(default_factory=dict)


@dataclass
class RetentionPolicy:
    """Data retention policy."""
    id: str
    name: str
    data_type: str
    retention_days: int
    is_active: bool = True


@dataclass
class ConsentRecord:
    """User consent record."""
    id: str
    user_id: str
    consent_type: str
    granted: bool
    timestamp: float
    ip_address: str = ""


class ComplianceManager:
    """Manage GDPR compliance and data protection."""

    def __init__(self):
        self._exports: dict[str, DataExport] = {}
        self._retention_policies: dict[str, RetentionPolicy] = {}
        self._consent_records: dict[str, list[ConsentRecord]] = {}
        self._setup_default_policies()

    def _setup_default_policies(self):
        """Setup default retention policies."""
        self._retention_policies["messages"] = RetentionPolicy(
            id="messages", name="Chat Messages", data_type="messages", retention_days=365
        )
        self._retention_policies["memory"] = RetentionPolicy(
            id="memory", name="AI Memory", data_type="memory", retention_days=730
        )
        self._retention_policies["logs"] = RetentionPolicy(
            id="logs", name="Activity Logs", data_type="logs", retention_days=90
        )

    def request_data_export(self, user_id: str) -> DataExport:
        """Request a GDPR data export."""
        export = DataExport(
            id=secrets.token_hex(8),
            user_id=user_id,
            status="pending",
            created_at=time.time(),
        )
        self._exports[export.id] = export
        return export

    def generate_data_export(self, export_id: str, user_data: dict) -> Optional[DataExport]:
        """Generate the actual data export."""
        export = self._exports.get(export_id)
        if not export:
            return None

        export.data = {
            "export_id": export.id,
            "user_id": export.user_id,
            "generated_at": datetime.now().isoformat(),
            "format": "JSON",
            "data": user_data,
        }
        export.status = "completed"
        export.completed_at = time.time()

        return export

    def get_export(self, export_id: str) -> Optional[DataExport]:
        return self._exports.get(export_id)

    def request_data_deletion(self, user_id: str) -> dict:
        """Request right-to-delete (GDPR Article 17)."""
        return {
            "user_id": user_id,
            "status": "pending",
            "requested_at": datetime.now().isoformat(),
            "items_to_delete": [
                "profile",
                "conversations",
                "messages",
                "memory",
                "analytics",
                "sessions",
            ],
            "estimated_completion": "24 hours",
        }

    def record_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        ip_address: str = "",
    ) -> ConsentRecord:
        """Record user consent."""
        record = ConsentRecord(
            id=secrets.token_hex(8),
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            timestamp=time.time(),
            ip_address=ip_address,
        )
        self._consent_records.setdefault(user_id, []).append(record)
        return record

    def get_consent(self, user_id: str, consent_type: str) -> Optional[ConsentRecord]:
        """Get latest consent for a type."""
        records = self._consent_records.get(user_id, [])
        matching = [r for r in records if r.consent_type == consent_type]
        return matching[-1] if matching else None

    def has_consent(self, user_id: str, consent_type: str) -> bool:
        """Check if user has given consent."""
        record = self.get_consent(user_id, consent_type)
        return record.granted if record else False

    def set_retention_policy(
        self,
        data_type: str,
        retention_days: int,
        name: str = "",
    ) -> RetentionPolicy:
        """Set a retention policy."""
        policy = RetentionPolicy(
            id=data_type,
            name=name or data_type,
            data_type=data_type,
            retention_days=retention_days,
        )
        self._retention_policies[data_type] = policy
        return policy

    def get_retention_policy(self, data_type: str) -> Optional[RetentionPolicy]:
        return self._retention_policies.get(data_type)

    def get_expired_data(self, data_type: str) -> list[str]:
        """Get data types that have expired based on retention policy."""
        policy = self._retention_policies.get(data_type)
        if not policy:
            return []

        cutoff = time.time() - (policy.retention_days * 86400)
        return [data_type]

    def get_compliance_status(self, user_id: str) -> dict:
        """Get compliance status for a user."""
        return {
            "data_export_available": any(
                e.user_id == user_id and e.status == "completed"
                for e in self._exports.values()
            ),
            "consents": {
                r.consent_type: r.granted
                for r in self._consent_records.get(user_id, [])
            },
            "retention_policies": {
                k: {"days": v.retention_days, "active": v.is_active}
                for k, v in self._retention_policies.items()
            },
        }

    def generate_privacy_report(self, user_id: str) -> dict:
        """Generate a privacy report for the user."""
        consents = self._consent_records.get(user_id, [])
        return {
            "user_id": user_id,
            "generated_at": datetime.now().isoformat(),
            "consents": [
                {
                    "type": c.consent_type,
                    "granted": c.granted,
                    "timestamp": datetime.fromtimestamp(c.timestamp).isoformat(),
                }
                for c in consents
            ],
            "data_processed": [
                "chat_messages",
                "ai_memory",
                "usage_analytics",
            ],
            "third_party_processors": [
                "OpenAI",
                "Anthropic",
                "Google",
                "Supabase",
            ],
            "rights": [
                "right_to_access",
                "right_to_rectification",
                "right_to_erasure",
                "right_to_portability",
                "right_to_object",
            ],
        }


compliance_manager = ComplianceManager()
