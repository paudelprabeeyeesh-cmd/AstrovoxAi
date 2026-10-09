
import uuid
from datetime import datetime, timezone
from typing import Optional
from .database import get_db


MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "llama-3.3-70b": {"input": 0.59, "output": 0.79},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
}


class CostTracker:
    def record_cost(self, user_id: str, model: str, prompt_tokens: int, completion_tokens: int, cost: float) -> str:
        event_id = str(uuid.uuid4())
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o"])
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analytics_events (id, event_type, properties, created_at) VALUES (?, ?, ?, ?)",
                (event_id, "cost", str({
                    "user_id": user_id,
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "cost": cost,
                    "pricing": pricing,
                }), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return event_id

    def get_user_cost(self, user_id: str, days: int = 30) -> dict:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            row = conn.execute(
                "SELECT SUM((properties->>'cost')::numeric) as total_cost, COUNT(*) as requests FROM analytics_events WHERE user_id = ? AND event_type = 'cost' AND created_at >= ?",
                (user_id, cutoff),
            ).fetchone()
            return {"user_id": user_id, "total_cost": float(row["total_cost"] or 0), "requests": row["requests"] or 0}

    def get_cost_trend(self, days: int = 7) -> list:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT date(created_at) as day, SUM((properties->>'cost')::numeric) as cost, COUNT(*) as requests FROM analytics_events WHERE event_type = 'cost' AND created_at >= ? GROUP BY date(created_at) ORDER BY day DESC",
                (cutoff,),
            ).fetchall()
            return [{"day": r["day"], "cost": round(float(r["cost"] or 0), 6), "requests": r["requests"]} for r in rows]

    def get_model_cost_breakdown(self, days: int = 7) -> list:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT properties->>'model' as model, SUM((properties->>'cost')::numeric) as cost, COUNT(*) as requests FROM analytics_events WHERE event_type = 'cost' AND created_at >= ? GROUP BY model ORDER BY cost DESC",
                (cutoff,),
            ).fetchall()
            return [{"model": r["model"], "cost": round(float(r["cost"] or 0), 6), "requests": r["requests"]} for r in rows]
