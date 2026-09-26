import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from app.repositories.database.client import get_db
from ...schemas import AdminStatsResponse, UsageResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


@router.get("/admin/stats", response_model=AdminStatsResponse)
async def get_admin_stats(_: str = Depends(require_admin)):
    try:
        with get_db() as conn:
            users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()
            conversations = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()
            messages = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()
            api_calls = conn.execute("SELECT COUNT(*) as c FROM interactions").fetchone()
            cost = conn.execute("SELECT SUM(cost_usd) as c FROM interactions").fetchone()
            active = conn.execute(
                "SELECT COUNT(DISTINCT user_id) as c FROM interactions WHERE created_at >= datetime('now', '-1 day')"
            ).fetchone()
        return AdminStatsResponse(
            total_users=users["c"] if users else 0,
            total_conversations=conversations["c"] if conversations else 0,
            total_messages=messages["c"] if messages else 0,
            total_api_calls=api_calls["c"] if api_calls else 0,
            total_cost_usd=float(cost["c"]) if cost and cost["c"] else 0.0,
            active_users_24h=active["c"] if active else 0,
        )
    except Exception as e:
        logger.error(f"Admin stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/usage/{user_id}", response_model=UsageResponse)
async def get_user_usage(user_id: str, _: str = Depends(require_admin)):
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT user_id, COUNT(*) as api_calls, SUM(tokens) as tokens_used, SUM(cost_usd) as cost_usd FROM interactions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return UsageResponse(
            user_id=row["user_id"],
            period="all",
            api_calls=row["api_calls"],
            tokens_used=row["tokens_used"] or 0,
            cost_usd=float(row["cost_usd"] or 0),
            by_model={},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User usage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/users")
async def list_users(_: str = Depends(require_admin)):
    with get_db() as conn:
        rows = conn.execute("SELECT id, email, created_at FROM users ORDER BY created_at DESC LIMIT 100").fetchall()
        return [dict(r) for r in rows]


@router.get("/admin/models")
async def list_admin_models(_: str = Depends(require_admin)):
    from ..model_catalog import model_router
    return model_router.list_models()
