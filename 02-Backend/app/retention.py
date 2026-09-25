import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    id: str
    name: str
    data_type: str
    retention_days: int
    is_active: bool = True
    action: str = "delete"
    created_at: float = field(default_factory=datetime.now(timezone.utc).timestamp)


class RetentionPolicyEngine:
    def __init__(self):
        self.policies: Dict[str, RetentionPolicy] = {}

    def create_policy(self, name: str, data_type: str, retention_days: int, action: str = "delete") -> RetentionPolicy:
        policy_id = str(uuid.uuid4())
        policy = RetentionPolicy(
            id=policy_id,
            name=name,
            data_type=data_type,
            retention_days=retention_days,
            action=action,
        )
        self.policies[data_type] = policy
        self._persist_policy(policy)
        logger.info("Created retention policy %s for %s", name, data_type)
        return policy

    def _persist_policy(self, policy: RetentionPolicy) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO retention_policies (id, name, data_type, retention_days, is_active, action) VALUES (?, ?, ?, ?, ?, ?)",
                (policy.id, policy.name, policy.data_type, policy.retention_days, 1 if policy.is_active else 0, policy.action),
            )
            conn.commit()

    def load_policies(self) -> None:
        with get_db() as conn:
            rows = conn.execute("SELECT id, name, data_type, retention_days, is_active, action FROM retention_policies").fetchall()
            for r in rows:
                policy = RetentionPolicy(
                    id=r["id"],
                    name=r["name"],
                    data_type=r["data_type"],
                    retention_days=r["retention_days"],
                    is_active=bool(r["is_active"]),
                    action=r["action"],
                )
                self.policies[policy.data_type] = policy

    def get_policy(self, data_type: str) -> Optional[RetentionPolicy]:
        return self.policies.get(data_type)

    def list_policies(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "data_type": p.data_type,
                "retention_days": p.retention_days,
                "is_active": p.is_active,
                "action": p.action,
            }
            for p in self.policies.values()
        ]

    def get_expired_data(self, data_type: str) -> List[str]:
        policy = self.policies.get(data_type)
        if not policy or not policy.is_active:
            return []
        cutoff = datetime.now(timezone.utc).timestamp() - (policy.retention_days * 86400)
        return [data_type]

    def enforce_retention(self, data_type: str, batch_size: int = 1000) -> Dict[str, Any]:
        policy = self.policies.get(data_type)
        if not policy or not policy.is_active:
            return {"status": "skipped", "reason": "policy not found or inactive"}

        cutoff = datetime.now(timezone.utc).timestamp() - (policy.retention_days * 86400)
        deleted = 0

        try:
            with get_db() as conn:
                if data_type == "messages":
                    cur = conn.execute(
                        "DELETE FROM messages WHERE created_at < datetime(?, 'unixepoch')",
                        (cutoff,),
                    )
                    deleted = cur.rowcount
                elif data_type == "memories":
                    cur = conn.execute(
                        "DELETE FROM memories WHERE created_at < datetime(?, 'unixepoch')",
                        (cutoff,),
                    )
                    deleted = cur.rowcount
                elif data_type == "audit_logs":
                    cur = conn.execute(
                        "DELETE FROM enterprise_audit_logs WHERE created_at < datetime(?, 'unixepoch')",
                        (cutoff,),
                    )
                    deleted = cur.rowcount
                conn.commit()
        except Exception as exc:
            logger.error("Retention enforcement failed for %s: %s", data_type, exc)
            return {"status": "error", "error": str(exc), "deleted": deleted}

        logger.info("Retention enforcement for %s: deleted %s rows", data_type, deleted)
        return {"status": "completed", "data_type": data_type, "deleted": deleted, "cutoff": cutoff}


retention_engine = RetentionPolicyEngine()
