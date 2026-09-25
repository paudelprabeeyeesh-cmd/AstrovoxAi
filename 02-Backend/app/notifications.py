
import uuid
from datetime import datetime, timezone
from repositories.database.client import get_db

def subscribe_to_notifications(user_id: str, endpoint: str, keys: str) -> dict:
    sub_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO notification_subscriptions (id, user_id, endpoint, keys, created_at) VALUES (?, ?, ?, ?, ?)",
            (sub_id, user_id, endpoint, keys, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return {"id": sub_id, "endpoint": endpoint}

def list_subscriptions(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, endpoint, created_at FROM notification_subscriptions WHERE user_id = ?", (user_id,)).fetchall()
        return [{"id": r["id"], "endpoint": r["endpoint"], "created_at": r["created_at"]} for r in rows]

def create_daily_digest(user_id: str, content: str) -> dict:
    digest_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO notification_digests (id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
            (digest_id, user_id, content, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return {"id": digest_id, "content": content}
