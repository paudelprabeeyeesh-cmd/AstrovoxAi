import uuid
from datetime import datetime, timezone

from .database import get_db


def create_post(user_id: str, title: str, content: str, author: str = "founder") -> dict:
    post_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO posts (id, user_id, title, content, author, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (post_id, user_id, title, content, author, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": post_id, "title": title}


def list_posts(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, content, author, created_at FROM posts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "author": r["author"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
