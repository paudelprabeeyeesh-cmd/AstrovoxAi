import json
import uuid
from datetime import datetime
from .database import get_db

def create_post(title: str, content: str, author: str = "founder") -> dict:
    post_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO posts (id, title, content, author, created_at) VALUES (?, ?, ?, ?, ?)",
                     (post_id, title, content, author, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": post_id, "title": title}

def list_posts() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, author, created_at FROM posts ORDER BY created_at DESC").fetchall()
        return [{"id": r["id"], "title": r["title"], "author": r["author"], "created_at": r["created_at"]} for r in rows]
