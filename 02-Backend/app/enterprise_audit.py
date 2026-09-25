import uuid
from datetime import datetime, timezone

from repositories.database.client import get_db


def create_audit_log(user_id: str, action: str, metadata: str = None) -> dict:
    log_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO enterprise_audit_logs (id, user_id, action, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (log_id, user_id, action, metadata, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": log_id, "action": action}


def list_audit_logs(user_id: str, limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, action, metadata, created_at FROM enterprise_audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "action": r["action"],
                "metadata": r["metadata"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
