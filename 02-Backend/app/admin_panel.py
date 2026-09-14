import os

from fastapi import APIRouter, Depends, HTTPException

from .database import get_db
from .auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

# Your admin identity comes from the signed JWT (Task 1.1), NEVER from a header string.
ADMIN_USER_IDS = {
    x.strip() for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()
}


def require_admin(
    user_id: str = Depends(get_current_user),
):  # get_user_id = your real JWT dependency from Task 1.1
    if user_id not in ADMIN_USER_IDS:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user_id


@router.get("/users")  # list all users
def list_users(admin: str = Depends(require_admin), limit: int = 100, offset: int = 0):
    limit = min(limit, 200)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, email, plan, created_at, stripe_customer_id FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/users/{user_id}/plan")  # give/remove premium (any plan string)
def set_plan(user_id: str, plan: str, admin: str = Depends(require_admin)):
    if plan not in ("free", "pro", "team"):
        raise HTTPException(status_code=400, detail="invalid plan")
    with get_db() as conn:
        cur = conn.execute("UPDATE users SET plan = ? WHERE id = ?", (plan, user_id))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="user not found")
    return {"ok": True, "user_id": user_id, "plan": plan}


@router.delete("/users/{user_id}")  # remove a user + all their data
def delete_user(user_id: str, admin: str = Depends(require_admin)):
    if user_id in ADMIN_USER_IDS:
        raise HTTPException(status_code=400, detail="cannot delete an admin")
    with get_db() as conn:
        for table in (
            "users",
            "conversations",
            "messages",
            "api_keys",
            "usage",
            "memories",
            "knowledge_documents",
            "teams",
            "feedback",
        ):
            try:
                conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
            except Exception:
                pass  # table may not have user_id column
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    return {"ok": True, "deleted": user_id}


@router.get("/stats")  # dashboard: counts + revenue view
def stats(admin: str = Depends(require_admin)):
    with get_db() as conn:
        return {
            "users": conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
            "pro": conn.execute(
                "SELECT COUNT(*) c FROM users WHERE plan='pro'"
            ).fetchone()["c"],
            "team": conn.execute(
                "SELECT COUNT(*) c FROM users WHERE plan='team'"
            ).fetchone()["c"],
        }
