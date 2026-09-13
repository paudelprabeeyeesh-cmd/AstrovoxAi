import sqlite3
import os
from datetime import datetime, timedelta
from .database import DB_PATH

def get_usage(user_id: str = None, days: int = 30) -> dict:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        where = "WHERE created_at >= ?"
        params = [cutoff]
        if user_id:
            where += " AND user_id = ?"
            params.append(user_id)
        rows = conn.execute(f"SELECT COUNT(*) as total_requests, SUM(tokens) as total_tokens, SUM(cost) as total_cost FROM usage {where}", params).fetchone()
        return {
            "total_requests": rows["total_requests"] or 0,
            "total_tokens": rows["total_tokens"] or 0,
            "total_cost": round(rows["total_cost"] or 0, 4),
        }

def get_daily_cost(days: int = 7) -> list[dict]:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT date(created_at) as day, SUM(cost) as cost, COUNT(*) as requests
            FROM usage
            WHERE created_at >= ?
            GROUP BY date(created_at)
            ORDER BY day DESC
        """, (cutoff,)).fetchall()
        return [{"day": r["day"], "cost": round(r["cost"] or 0, 4), "requests": r["requests"]} for r in rows]

def get_revenue(days: int = 30) -> dict:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT COUNT(*) as paying_users, SUM(amount) as revenue
            FROM subscriptions
            WHERE created_at >= ?
        """, (cutoff,)).fetchone()
        return {"paying_users": row["paying_users"] or 0, "revenue": round(row["revenue"] or 0, 2)}
