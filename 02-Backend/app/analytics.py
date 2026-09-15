import uuid
import json
from datetime import datetime, timedelta

from .database import get_db


def record_event(event_type: str, properties: dict):
    event_id = str(uuid.uuid4())
    payload = json.dumps(properties)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO analytics_events (id, event_type, properties, created_at) VALUES (?, ?, ?, ?)",
            (event_id, event_type, payload, datetime.utcnow().isoformat()),
        )
        conn.commit()
    return event_id


def track_event(event_name: str, properties: dict, user_id: str = None):
    event_id = str(uuid.uuid4())
    enriched = dict(properties or {})
    if user_id:
        enriched["user_id"] = user_id
    payload = json.dumps(enriched)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO analytics_events (id, event_type, properties, created_at) VALUES (?, ?, ?, ?)",
            (event_id, event_name, payload, datetime.utcnow().isoformat()),
        )
        conn.commit()
    return event_id


def get_aggregate_metrics(days: int = 7) -> dict:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT event_type, COUNT(*) as count, MIN(created_at) as first_seen, MAX(created_at) as last_seen
            FROM analytics_events
            WHERE created_at >= ?
            GROUP BY event_type
            ORDER BY count DESC
            """,
            (cutoff,),
        ).fetchall()
        return {
            "window_days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "events": [
                {
                    "event_type": r["event_type"],
                    "count": r["count"],
                    "first_seen": r["first_seen"],
                    "last_seen": r["last_seen"],
                }
                for r in rows
            ],
        }


def get_top_models(days: int = 7, limit: int = 10) -> list[dict]:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT properties->>'model' as model, COUNT(*) as count
            FROM analytics_events
            WHERE event_type = 'llm_call' AND created_at >= ?
            GROUP BY model
            ORDER BY count DESC
            LIMIT ?
            """,
            (cutoff, limit),
        ).fetchall()
        return [{"model": r["model"], "count": r["count"]} for r in rows]


def get_cost_trend(days: int = 7) -> list[dict]:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT date(created_at) as day, COUNT(*) as requests, SUM((properties->>'cost')::numeric) as cost
            FROM analytics_events
            WHERE event_type = 'llm_call' AND created_at >= ?
            GROUP BY date(created_at)
            ORDER BY day DESC
            """,
            (cutoff,),
        ).fetchall()
        return [
            {
                "day": r["day"],
                "requests": r["requests"],
                "cost": round(float(r["cost"] or 0), 6),
            }
            for r in rows
        ]
