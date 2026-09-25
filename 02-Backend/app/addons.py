import uuid

from app.repositories.database.client import get_db


def create_addon(
    user_id: str, type_: str, amount: float, stripe_price_id: str = None
) -> str:
    addon_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO addons (id, user_id, type, amount, stripe_price_id) VALUES (?, ?, ?, ?, ?)",
            (addon_id, user_id, type_, amount, stripe_price_id),
        )
        conn.commit()
    return addon_id


def list_addons(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, type, amount, stripe_price_id, created_at FROM addons WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "type": r["type"],
                "amount": r["amount"],
                "stripe_price_id": r["stripe_price_id"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]


def get_addon_cost(user_id: str) -> float:
    with get_db() as conn:
        row = conn.execute(
            "SELECT SUM(amount) as total FROM addons WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["total"] or 0.0
