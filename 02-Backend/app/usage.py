import uuid
import uuid
import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("ASTROVOX_DB", "astrovox.db")

def record_usage(user_id: str, tokens: int, cost: float, model: str, cached: bool = False, error: str = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO usage (id, user_id, tokens, cost, model, cached, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), user_id, tokens, cost, model, int(cached), error, datetime.utcnow().isoformat()))
        conn.commit()
