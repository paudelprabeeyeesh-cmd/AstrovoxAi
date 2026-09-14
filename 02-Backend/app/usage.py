import os
import sqlite3
import uuid
from datetime import datetime

DB_PATH = os.getenv("ASTROVOX_DB", "astrovox.db")


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
            "CREATE TABLE IF NOT EXISTS usage (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, tokens INTEGER NOT NULL, cost REAL NOT NULL, model TEXT NOT NULL, cached INTEGER DEFAULT 0, error TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        _conn.commit()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
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
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
