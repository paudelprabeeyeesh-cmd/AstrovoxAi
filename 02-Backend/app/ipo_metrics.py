import json
import uuid
from datetime import datetime
from .database import get_db

def create_ipo_metric(name: str, target: str, current: str) -> dict:
    metric_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO ipo_metrics (id, name, target, current, created_at) VALUES (?, ?, ?, ?, ?)",
                     (metric_id, name, target, current, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": metric_id, "name": name}

def list_ipo_metrics() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, target, current, created_at FROM ipo_metrics ORDER BY created_at DESC").fetchall()
        return [{"id": r["id"], "name": r["name"], "target": r["target"], "current": r["current"], "created_at": r["created_at"]} for r in rows]
