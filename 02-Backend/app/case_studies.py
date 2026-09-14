import uuid
from datetime import datetime

from .database import get_db


def create_case_study(title: str, content: str, user_id: str) -> dict:
    case_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO case_studies (id, title, content, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (case_id, title, content, user_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
    return {"id": case_id, "title": title}


def list_case_studies() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, content, user_id, created_at FROM case_studies ORDER BY created_at DESC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "content": r["content"],
                "user_id": r["user_id"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
