import uuid
from datetime import datetime
from .database import get_db

def create_prompt(user_id: str, title: str, prompt: str, price: float = 0) -> str:
    prompt_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO marketplace_prompts (id, user_id, title, prompt, price) VALUES (?, ?, ?, ?, ?)",
                     (prompt_id, user_id, title, prompt, price))
        conn.commit()
    return prompt_id

def list_prompts() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, prompt, price, downloads, created_at FROM marketplace_prompts ORDER BY downloads DESC").fetchall()
        return [{"id": r["id"], "title": r["title"], "prompt": r["prompt"], "price": r["price"], "downloads": r["downloads"], "created_at": r["created_at"]} for r in rows]

def get_prompt(prompt_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT id, title, prompt, price, downloads, created_at FROM marketplace_prompts WHERE id = ?", (prompt_id,)).fetchone()
        if not row:
            raise ValueError("Prompt not found")
        return {"id": row["id"], "title": row["title"], "prompt": row["prompt"], "price": row["price"], "downloads": row["downloads"], "created_at": row["created_at"]}

def increment_downloads(prompt_id: str):
    with get_db() as conn:
        conn.execute("UPDATE marketplace_prompts SET downloads = downloads + 1 WHERE id = ?", (prompt_id,))
        conn.commit()
