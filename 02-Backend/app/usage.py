import uuid
from datetime import datetime, timezone

from .database import get_db


def record_usage(
    user_id: str,
    tokens: int,
    cost: float,
    model: str,
    cached: bool = False,
    error: str = None,
):
    with get_db() as _conn:
        _conn.execute(
            """
            INSERT INTO usage (id, user_id, tokens, cost, model, cached, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                str(uuid.uuid4()),
                user_id,
                tokens,
                cost,
                model,
                int(cached),
                error,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        _conn.commit()
