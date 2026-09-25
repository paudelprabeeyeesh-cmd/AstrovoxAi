import uuid
from datetime import datetime, timezone

from app.repositories.database.client import get_db


def create_interaction(
    user_id: str,
    prompt: str,
    response: str,
    model: str,
    tokens: int,
    cost: float,
    latency_ms: int = None,
) -> dict:
    interaction_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO interactions (id, user_id, prompt, response, model, tokens, cost, latency_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                interaction_id,
                user_id,
                prompt,
                response,
                model,
                tokens,
                cost,
                latency_ms,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    return {"id": interaction_id}


def update_interaction_feedback(interaction_id: str, rating: int, correction: str = None):
    with get_db() as conn:
        conn.execute(
            "UPDATE interactions SET rating = ?, correction = ? WHERE id = ?",
            (rating, correction, interaction_id),
        )
        conn.commit()


def get_user_interactions(user_id: str, limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, prompt, response, model, tokens, cost, rating, correction, created_at FROM interactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "prompt": r["prompt"],
                "response": r["response"],
                "model": r["model"],
                "tokens": r["tokens"],
                "cost": r["cost"],
                "rating": r["rating"],
                "correction": r["correction"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
