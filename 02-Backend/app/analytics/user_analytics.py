
from datetime import datetime, timezone, timedelta
from .enhanced import get_user_analytics, get_organization_analytics, get_workspace_analytics


class UserAnalyticsService:
    def get_user_dashboard(self, user_id: str, days: int = 30) -> dict:
        return get_user_analytics(user_id, days)

    def get_user_activity_timeline(self, user_id: str, days: int = 7) -> list:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        from ..database import get_db
        with get_db() as conn:
            rows = conn.execute(
                "SELECT event_type, created_at, properties FROM analytics_events WHERE user_id = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 100",
                (user_id, cutoff),
            ).fetchall()
            return [{"event_type": r["event_type"], "created_at": r["created_at"], "properties": r["properties"]} for r in rows]

    def get_user_retention(self, user_id: str) -> dict:
        from ..database import get_db
        with get_db() as conn:
            first = conn.execute("SELECT MIN(created_at) as first FROM analytics_events WHERE user_id = ?", (user_id,)).fetchone()
            last = conn.execute("SELECT MAX(created_at) as last FROM analytics_events WHERE user_id = ?", (user_id,)).fetchone()
            count = conn.execute("SELECT COUNT(*) as cnt FROM analytics_events WHERE user_id = ?", (user_id,)).fetchone()
            return {
                "user_id": user_id,
                "first_seen": first["first"] if first else None,
                "last_seen": last["last"] if last else None,
                "total_events": count["cnt"] if count else 0,
            }
