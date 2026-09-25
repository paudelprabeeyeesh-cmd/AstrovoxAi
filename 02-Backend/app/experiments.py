import uuid
import json
from datetime import datetime, timezone

from repositories.database.client import get_db


def create_experiment(name: str, hypothesis: str, variants: list[str], traffic_split: list[float], owner_id: str) -> dict:
    experiment_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO experiments (id, name, hypothesis, variants, traffic_split, owner_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                name,
                hypothesis,
                json.dumps(variants),
                json.dumps(traffic_split),
                owner_id,
                "active",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    return {
        "id": experiment_id,
        "name": name,
        "variants": variants,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def assign_variant(experiment_id: str, user_id: str) -> str:
    with get_db() as conn:
        row = conn.execute(
            "SELECT variants, traffic_split FROM experiments WHERE id = ? AND status = 'active'",
            (experiment_id,),
        ).fetchone()
        if not row:
            raise ValueError("Experiment not found")
        variants = json.loads(row["variants"])
        splits = json.loads(row["traffic_split"])
        assignment = conn.execute(
            "SELECT variant FROM experiment_assignments WHERE experiment_id = ? AND user_id = ?",
            (experiment_id, user_id),
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
            "INSERT INTO experiment_assignments (id, experiment_id, user_id, variant) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), experiment_id, user_id, chosen),
        )
        conn.commit()
        return chosen


def record_win(experiment_id: str, variant: str, metric: str, value: float, user_id: str | None = None):
    win_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO experiment_results (id, experiment_id, variant, metric, value, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (win_id, experiment_id, variant, metric, value, user_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def get_winner(experiment_id: str, metric: str = "conversion") -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM experiment_results WHERE experiment_id = ?",
            (experiment_id,),
        ).fetchone()
        if not row or row["cnt"] < 30:
            return None
        rows = conn.execute(
            """
            SELECT variant, AVG(value) as avg_value, COUNT(*) as samples
            FROM experiment_results
            WHERE experiment_id = ? AND metric = ?
            GROUP BY variant
            ORDER BY avg_value DESC
            """,
            (experiment_id, metric),
        ).fetchall()
        if not rows:
            return None
        best = rows[0]
        return {
            "variant": best["variant"],
            "metric": metric,
            "avg_value": round(float(best["avg_value"]), 4),
            "samples": best["samples"],
            "all_variants": [
                {"variant": r["variant"], "avg_value": round(float(r["avg_value"]), 4), "samples": r["samples"]}
                for r in rows
            ],
        }


def list_experiments(owner_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, hypothesis, variants, status, created_at FROM experiments WHERE owner_id = ? ORDER BY created_at DESC",
            (owner_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "hypothesis": r["hypothesis"],
                "variants": json.loads(r["variants"]),
                "status": r["status"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
