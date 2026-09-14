import json
import random
import uuid

from .database import get_db


def create_test(name: str, variants: list[str], traffic_split: list[float]) -> str:
    test_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ab_tests (id, name, variants, traffic_split) VALUES (?, ?, ?, ?)",
            (test_id, name, json.dumps(variants), json.dumps(traffic_split)),
        )
        conn.commit()
    return test_id


def assign_variant(test_id: str, user_id: str) -> str:
    with get_db() as conn:
        row = conn.execute(
            "SELECT variants, traffic_split FROM ab_tests WHERE id = ?", (test_id,)
        ).fetchone()
        if not row:
            raise ValueError("Test not found")
        variants = json.loads(row["variants"])
        splits = json.loads(row["traffic_split"])
        assignment = conn.execute(
            "SELECT variant FROM ab_assignments WHERE test_id = ? AND user_id = ?",
            (test_id, user_id),
        ).fetchone()
        if assignment:
            return assignment["variant"]
        r = random.random()
        cumulative = 0.0
        chosen = variants[0]
        for v, s in zip(variants, splits):
            cumulative += s
            if r <= cumulative:
                chosen = v
                break
        conn.execute(
            "INSERT INTO ab_assignments (id, test_id, user_id, variant) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), test_id, user_id, chosen),
        )
        conn.commit()
        return chosen


def record_result(test_id: str, variant: str, metric: str, value: float):
    with get_db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ab_test_results (id TEXT PRIMARY KEY, test_id TEXT NOT NULL, variant TEXT NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.execute(
            "INSERT INTO ab_test_results (id, test_id, variant, metric, value) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), test_id, variant, metric, value),
        )
        conn.commit()


def select_winner(test_id: str, metric: str = "conversion") -> str | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM ab_test_results WHERE test_id = ?", (test_id,)
        ).fetchone()
        if not row or row["cnt"] < 100:
            return None
        rows = conn.execute(
            "SELECT variant, AVG(value) as avg_value FROM ab_test_results WHERE test_id = ? AND metric = ? GROUP BY variant",
            (test_id, metric),
        ).fetchall()
        if not rows:
            return None
        best = max(rows, key=lambda r: r["avg_value"])
        return best["variant"]
