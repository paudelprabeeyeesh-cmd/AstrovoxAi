import uuid
import json
import random
from datetime import datetime
from .database import get_db

def create_test(name: str, variants: list[str], traffic_split: list[float]) -> str:
    test_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO ab_tests (id, name, variants, traffic_split) VALUES (?, ?, ?, ?)",
                     (test_id, name, json.dumps(variants), json.dumps(traffic_split)))
        conn.commit()
    return test_id

def assign_variant(test_id: str, user_id: str) -> str:
    with get_db() as conn:
        row = conn.execute("SELECT variants, traffic_split FROM ab_tests WHERE id = ?", (test_id,)).fetchone()
        if not row:
            raise ValueError("Test not found")
        variants = json.loads(row["variants"])
        splits = json.loads(row["traffic_split"])
        assignment = conn.execute("SELECT variant FROM ab_assignments WHERE test_id = ? AND user_id = ?", (test_id, user_id)).fetchone()
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
        conn.execute("INSERT INTO ab_assignments (id, test_id, user_id, variant) VALUES (?, ?, ?, ?)",
                     (str(uuid.uuid4()), test_id, user_id, chosen))
        conn.commit()
        return chosen
