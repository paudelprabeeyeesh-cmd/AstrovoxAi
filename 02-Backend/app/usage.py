import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional


class UsageQuotaExceeded(Exception):
    """Raised when a user exceeds the daily AI usage quota."""


class DailyUsageTracker:
    """File-backed daily usage tracker that survives process restarts."""

    def __init__(self, limit: Optional[int] = None, storage_path: Optional[str] = None):
        self.limit = int(limit or os.getenv("DAILY_AI_LIMIT", "50"))
        self.storage_path = storage_path or os.getenv("USAGE_DB_PATH", "./usage.db")
        self._initialize_db()

    def _initialize_db(self) -> None:
        directory = os.path.dirname(self.storage_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_events (
                    user_id TEXT NOT NULL,
                    day TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, day)
                )
                """
            )
            conn.commit()

    def _today_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async def record_success(self, user_id: str) -> int:
        today = self._today_key()
        with sqlite3.connect(self.storage_path) as conn:
            row = conn.execute(
                "SELECT count FROM usage_events WHERE user_id = ? AND day = ?",
                (user_id, today),
            ).fetchone()
            count = 0 if row is None else int(row[0])
            count += 1
            if count > self.limit:
                raise UsageQuotaExceeded(f"Daily AI quota exceeded: {self.limit}")
            conn.execute(
                "INSERT INTO usage_events(user_id, day, count) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, day) DO UPDATE SET count = excluded.count",
                (user_id, today, count),
            )
            conn.commit()
            return count

    async def get_count(self, user_id: str) -> int:
        today = self._today_key()
        with sqlite3.connect(self.storage_path) as conn:
            row = conn.execute(
                "SELECT count FROM usage_events WHERE user_id = ? AND day = ?",
                (user_id, today),
            ).fetchone()
            return 0 if row is None else int(row[0])
