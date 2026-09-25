import json
import uuid
from datetime import datetime, timezone

from app.repositories.database.client import get_db


def create_ab_test(name: str, variants: list[str], traffic_split: list[float]) -> str:
    test_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ab_tests (id, name, variants, traffic_split, active) VALUES (?, ?, ?, ?, ?)",
            (test_id, name, json.dumps(variants), json.dumps(traffic_split), 1),
        )
        conn.commit()
    return test_id


def get_variant(test_id: str, user_id: str) -> str:
    with get_db() as conn:
        row = conn.execute(
            "SELECT variants, traffic_split FROM ab_tests WHERE id = ? AND active = 1",
            (test_id,),
        ).fetchone()
        if not row:
            return ""
        variants = json.loads(row["variants"])
        splits = json.loads(row["traffic_split"])
        assignment = conn.execute(
            "SELECT variant FROM ab_assignments WHERE test_id = ? AND user_id = ?",
            (test_id, user_id),
        ).fetchone()
        if assignment:
            return assignment["variant"]
        import random

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
            "INSERT INTO ab_results (id, test_id, variant, metric, value, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                test_id,
                variant,
                metric,
                value,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
