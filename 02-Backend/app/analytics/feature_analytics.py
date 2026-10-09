
from datetime import datetime, timezone
from .database import get_db


class FeatureAnalyticsService:
    def track_feature_use(self, user_id: str, feature: str, metadata: dict = None) -> str:
        event_id = __import__("uuid").uuid4().hex
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analytics_events (id, event_type, properties, created_at) VALUES (?, ?, ?, ?)",
                (event_id, "feature_use", str({"user_id": user_id, "feature": feature, "metadata": metadata or {}}), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return event_id

    def get_feature_usage(self, days: int = 7) -> dict:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT properties->>'feature' as feature, COUNT(*) as count FROM analytics_events WHERE event_type = 'feature_use' AND created_at >= ? GROUP BY feature ORDER BY count DESC",
                (cutoff,),
            ).fetchall()
            return {"window_days": days, "features": [{"feature": r["feature"], "count": r["count"]} for r in rows]}

    def get_feature_adoption(self) -> dict:
        with get_db() as conn:
            total_users = conn.execute("SELECT COUNT(DISTINCT user_id) as cnt FROM analytics_events").fetchone()
            feature_users = conn.execute(
                "SELECT properties->>'feature' as feature, COUNT(DISTINCT user_id) as users FROM analytics_events WHERE event_type = 'feature_use' GROUP BY feature"
            ).fetchall()
            total = total_users["cnt"] if total_users else 0
            return {
                "total_users": total,
                "features": [{"feature": r["feature"], "users": r["users"], "adoption_rate": round(r["users"] / total, 4) if total else 0} for r in feature_users],
            }
