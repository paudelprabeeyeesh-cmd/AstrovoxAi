import uuid
from datetime import datetime, timezone

from .database import get_db


def create_ama(user_id: str, title: str, description: str, scheduled_at: str) -> dict:
    ama_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO amas (id, user_id, title, description, scheduled_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ama_id, user_id, title, description, scheduled_at, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": ama_id, "title": title}


def list_amas(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, description, scheduled_at, created_at FROM amas WHERE user_id = ? ORDER BY scheduled_at DESC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "description": r["description"],
                "scheduled_at": r["scheduled_at"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
