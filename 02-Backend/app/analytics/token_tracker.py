
import uuid
from datetime import datetime, timezone
from typing import Optional
from .database import get_db


class TokenTracker:
    def track_tokens(self, user_id: str, model: str, prompt_tokens: int, completion_tokens: int, cached: bool = False) -> str:
        event_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analytics_events (id, event_type, properties, created_at) VALUES (?, ?, ?, ?)",
                (event_id, "tokens", str({
                    "user_id": user_id,
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "cached": cached,
                }), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return event_id

    def get_user_tokens(self, user_id: str, days: int = 30) -> dict:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            row = conn.execute(
                "SELECT SUM((properties->>'total_tokens')::numeric) as total_tokens, COUNT(*) as requests FROM analytics_events WHERE user_id = ? AND event_type = 'tokens' AND created_at >= ?",
                (user_id, cutoff),
            ).fetchone()
            return {"user_id": user_id, "total_tokens": int(row["total_tokens"] or 0), "requests": row["requests"] or 0}

    def get_token_trend(self, days: int = 7) -> list:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT date(created_at) as day, SUM((properties->>'total_tokens')::numeric) as tokens, COUNT(*) as requests FROM analytics_events WHERE event_type = 'tokens' AND created_at >= ? GROUP BY date(created_at) ORDER BY day DESC",
                (cutoff,),
            ).fetchall()
            return [{"day": r["day"], "tokens": int(r["tokens"] or 0), "requests": r["requests"]} for r in rows]

    def get_model_token_breakdown(self, days: int = 7) -> list:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT properties->>'model' as model, SUM((properties->>'total_tokens')::numeric) as tokens, COUNT(*) as requests FROM analytics_events WHERE event_type = 'tokens' AND created_at >= ? GROUP BY model ORDER BY tokens DESC",
                (cutoff,),
            ).fetchall()
            return [{"model": r["model"], "tokens": int(r["tokens"] or 0), "requests": r["requests"]} for r in rows]
