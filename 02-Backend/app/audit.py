import uuid
from datetime import datetime, timezone
from typing import Optional
from repositories.database.client import get_db


def log_action(user_id: str, action: str, resource: str = "", details: Optional[dict] = None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO audit_logs (id, user_id, action, resource, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, action, resource, str(details) if details else None, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def get_audit_log(user_id: str, limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT action, resource, details, created_at FROM audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            {
                "action": r["action"],
                "resource": r["resource"],
                "details": r["details"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
