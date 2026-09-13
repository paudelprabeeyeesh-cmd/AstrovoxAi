import json
import uuid
from datetime import datetime
from .database import get_db

def create_ama(title: str, description: str, scheduled_at: str) -> dict:
    ama_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO amas (id, title, description, scheduled_at, created_at) VALUES (?, ?, ?, ?, ?)",
                     (ama_id, title, description, scheduled_at, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": ama_id, "title": title}

def list_amas() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, description, scheduled_at, created_at FROM amas ORDER BY scheduled_at DESC").fetchall()
        return [{"id": r["id"], "title": r["title"], "description": r["description"], "scheduled_at": r["scheduled_at"], "created_at": r["created_at"]} for r in rows]
