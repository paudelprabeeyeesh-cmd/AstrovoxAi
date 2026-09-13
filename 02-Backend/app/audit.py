import uuid
from datetime import datetime
from .database import get_db

def log_action(user_id: str, action: str, metadata: str = None):
    with get_db() as conn:
        conn.execute("INSERT INTO audit_logs (id, user_id, action, metadata) VALUES (?, ?, ?, ?)",
                     (str(uuid.uuid4()), user_id, action, metadata))
        conn.commit()

def get_audit_logs(user_id: str, limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT action, metadata, created_at FROM audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
        return [{"action": r["action"], "metadata": r["metadata"], "created_at": r["created_at"]} for r in rows]
