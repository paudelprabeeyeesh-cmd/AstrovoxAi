import sqlite3
from datetime import datetime, timedelta, timezone

from .database import DB_PATH


def get_usage(user_id: str = None, days: int = 30) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        where = "WHERE created_at >= ?"
        params = [cutoff]
        if user_id:
            where += " AND user_id = ?"
            params.append(user_id)
        rows = conn.execute(
            f"SELECT COUNT(*) as total_requests, SUM(tokens) as total_tokens, SUM(cost) as total_cost FROM interactions {where}",
            params,
        ).fetchone()
        return {
            "total_requests": rows["total_requests"] or 0,
            "total_tokens": rows["total_tokens"] or 0,
            "total_cost": round(rows["total_cost"] or 0, 4),
        }


def get_daily_cost(days: int = 7) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT date(created_at) as day, SUM(cost) as cost, COUNT(*) as requests
            FROM interactions
            WHERE created_at >= ?
            GROUP BY date(created_at)
            ORDER BY day DESC
        """,
            (cutoff,),
        ).fetchall()
        return [
            {
                "day": r["day"],
                "cost": round(r["cost"] or 0, 4),
                "requests": r["requests"],
            }
            for r in rows
        ]


def get_revenue(days: int = 30) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT COUNT(*) as paying_users, SUM(amount) as revenue
            FROM subscriptions
            WHERE created_at >= ?
        """,
            (cutoff,),
        ).fetchone()
        return {
            "paying_users": row["paying_users"] or 0,
            "revenue": round(row["revenue"] or 0, 2),
        }


def get_second_use_metric(days: int = 7) -> dict:
    """Calculate % of users who called /solve twice within 7 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        # Users with at least 2 interactions in the period
        row = conn.execute(
            """
            SELECT COUNT(*) as returning_users FROM (
                SELECT user_id
                FROM interactions
                WHERE created_at >= ?
                GROUP BY user_id
                HAVING COUNT(*) >= 2
            )
        """,
            (cutoff,),
        ).fetchone()
        
        returning = row["returning_users"] or 0
        
        # Total unique users in the period
        row2 = conn.execute(
            """
            SELECT COUNT(DISTINCT user_id) as total_users
            FROM interactions
            WHERE created_at >= ?
            """,
            (cutoff,),
        ).fetchone()
        
        total = row2["total_users"] or 0
        rate = (returning / total * 100) if total > 0 else 0
        
        return {
            "returning_users": returning,
            "total_users": total,
            "second_use_rate": round(rate, 2),
        }
