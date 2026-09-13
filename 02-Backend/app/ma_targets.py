import json
import uuid
from datetime import datetime
from .database import get_db

def create_ma_target(name: str, description: str, valuation: float) -> dict:
    target_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO ma_targets (id, name, description, valuation, created_at) VALUES (?, ?, ?, ?, ?)",
                     (target_id, name, description, valuation, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": target_id, "name": name, "valuation": valuation}

def list_ma_targets() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, description, valuation, created_at FROM ma_targets ORDER BY created_at DESC").fetchall()
        return [{"id": r["id"], "name": r["name"], "description": r["description"], "valuation": r["valuation"], "created_at": r["created_at"]} for r in rows]
