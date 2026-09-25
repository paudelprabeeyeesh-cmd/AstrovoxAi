import uuid
from datetime import datetime, timezone

from repositories.database.client import get_db


def create_comment(post_id: str, user_id: str, content: str) -> dict:
    comment_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO comments (id, post_id, user_id, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (comment_id, post_id, user_id, content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": comment_id, "post_id": post_id}


def list_comments(post_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, user_id, content, created_at FROM comments WHERE post_id = ? ORDER BY created_at ASC",
            (post_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "content": r["content"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
