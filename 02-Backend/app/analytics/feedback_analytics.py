
from datetime import datetime, timezone
from .database import get_db
from ..feedback import create_feedback, list_feedback, delete_feedback


class FeedbackAnalyticsService:
    def record_feedback(self, user_id: str, request_id: str, rating: int, comment: str = "") -> dict:
        fb = create_feedback(user_id, type("FeedbackCreate", (), {"request_id": request_id, "rating": rating, "comment": comment}))
        return {"id": fb.id, "rating": fb.rating, "comment": fb.comment, "created_at": fb.created_at.isoformat()}

    def get_feedback_summary(self, days: int = 30) -> dict:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT rating, COUNT(*) as count FROM feedback WHERE created_at >= ? GROUP BY rating ORDER BY rating",
                (cutoff,),
            ).fetchall()
            total = sum(r["count"] for r in rows)
            avg = sum(r["rating"] * r["count"] for r in rows) / total if total else 0
            return {"total_feedback": total, "average_rating": round(avg, 2), "distribution": [dict(r) for r in rows]}

    def get_recent_feedback(self, limit: int = 50) -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, user_id, request_id, rating, comment, created_at FROM feedback ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
