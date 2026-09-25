import uuid
from datetime import datetime, timezone

from repositories.database.client import get_db


def create_ipo_metric(user_id: str, name: str, target: str, current: str) -> dict:
    metric_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ipo_metrics (id, user_id, name, target, current, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (metric_id, user_id, name, target, current, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": metric_id, "name": name}


def list_ipo_metrics(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, target, current, created_at FROM ipo_metrics WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "target": r["target"],
                "current": r["current"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
