import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email, require_admin
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])


@router.get("/analytics/dashboard")
async def get_dashboard(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        messages = conn.execute(
            "SELECT COUNT(*) as c FROM messages m JOIN conversations c ON c.id = m.conversation_id WHERE c.user_id = ?",
            (user_id,),
        ).fetchone()
        tokens = conn.execute(
            "SELECT SUM(tokens) as c FROM interactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        cost = conn.execute(
            "SELECT SUM(cost_usd) as c FROM interactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        models = conn.execute(
            "SELECT model, COUNT(*) as cnt, SUM(tokens) as total_tokens FROM interactions WHERE user_id = ? GROUP BY model ORDER BY cnt DESC LIMIT 10",
            (user_id,),
        ).fetchall()
    return {
        "total_messages": messages["c"] if messages else 0,
        "total_tokens": tokens["c"] if tokens else 0,
        "total_cost_usd": float(cost["c"]) if cost and cost["c"] else 0.0,
        "top_models": [dict(r) for r in models],
    }


@router.get("/analytics/usage")
async def get_usage_analytics(period: str = "7d", user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DATE(created_at) as date, COUNT(*) as count, SUM(tokens) as tokens, SUM(cost_usd) as cost FROM interactions WHERE user_id = ? AND created_at >= datetime('now', ?) GROUP BY DATE(created_at) ORDER BY date DESC",
            (user_id, f"-{period}"),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/analytics/admin/overview")
async def get_admin_overview(_: str = Depends(require_admin)):
    with get_db() as conn:
        users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()
        messages = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()
        cost = conn.execute("SELECT SUM(cost_usd) as c FROM interactions").fetchone()
        active = conn.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM interactions WHERE created_at >= datetime('now', '-1 day')"
        ).fetchone()
    return {
        "total_users": users["c"] if users else 0,
        "total_messages": messages["c"] if messages else 0,
        "total_cost": float(cost["c"]) if cost and cost["c"] else 0.0,
        "active_users_24h": active["c"] if active else 0,
    }
