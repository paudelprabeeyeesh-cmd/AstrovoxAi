
import uuid
from datetime import datetime, timezone
from typing import Optional
from .database import get_db


class UsageTracker:
    def track_usage(self, user_id: str, action: str, metadata: Optional[dict] = None) -> str:
        event_id = str(uuid.uuid4())
        payload = {
            "user_id": user_id,
            "action": action,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analytics_events (id, event_type, properties, created_at) VALUES (?, ?, ?, ?)",
                (event_id, "usage", str(payload), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return event_id

    def get_user_usage(self, user_id: str, days: int = 30) -> dict:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT event_type, COUNT(*) as count FROM analytics_events WHERE user_id = ? AND event_type = 'usage' AND created_at >= ? GROUP BY event_type",
                (user_id, cutoff),
            ).fetchall()
            return {"user_id": user_id, "usage_count": sum(r["count"] for r in rows), "actions": [dict(r) for r in rows]}

    def get_top_usage_actions(self, days: int = 7, limit: int = 10) -> list:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT properties->>'action' as action, COUNT(*) as count FROM analytics_events WHERE event_type = 'usage' AND created_at >= ? GROUP BY action ORDER BY count DESC LIMIT ?",
                (cutoff, limit),
            ).fetchall()
            return [{"action": r["action"], "count": r["count"]} for r in rows]
