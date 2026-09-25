
import uuid
import csv
import io
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from app.repositories.database.client import get_db


def _get_org_members(org_id: str) -> List[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_id FROM organization_members WHERE org_id = ?",
            (org_id,),
        ).fetchall()
        return [r["user_id"] for r in rows]


def _get_workspace_members(workspace_id: str) -> List[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_id FROM workspace_members WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchall()
        return [r["user_id"] for r in rows]


def get_organization_analytics(org_id: str, days: int = 30) -> dict:
    members = _get_org_members(org_id)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT event_type, COUNT(*) as count, MIN(created_at) as first_seen, MAX(created_at) as last_seen
            FROM analytics_events
            WHERE created_at >= ? AND user_id IN ({})
            GROUP BY event_type
            ORDER BY count DESC
            """.format(",".join("?" * len(members))),
            [cutoff] + members,
        ).fetchall()
        events = [dict(r) for r in rows]

        usage_rows = conn.execute(
            """
            SELECT SUM(tokens) as total_tokens, SUM(cost) as total_cost, COUNT(*) as total_requests
            FROM usage
            WHERE created_at >= ? AND user_id IN ({})
            """.format(",".join("?" * len(members))),
            [cutoff] + members,
        ).fetchone()

    return {
        "org_id": org_id,
        "window_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "member_count": len(members),
        "events": events,
        "usage": dict(usage_rows) if usage_rows else {},
    }


def get_workspace_analytics(workspace_id: str, days: int = 30) -> dict:
    members = _get_workspace_members(workspace_id)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT event_type, COUNT(*) as count
            FROM analytics_events
            WHERE created_at >= ? AND user_id IN ({})
            GROUP BY event_type
            ORDER BY count DESC
            """.format(",".join("?" * len(members))),
            [cutoff] + members,
        ).fetchall()

        usage_rows = conn.execute(
            """
            SELECT SUM(tokens) as total_tokens, SUM(cost) as total_cost, COUNT(*) as total_requests
            FROM usage
            WHERE created_at >= ? AND user_id IN ({})
            """.format(",".join("?" * len(members))),
            [cutoff] + members,
        ).fetchone()

    return {
        "workspace_id": workspace_id,
        "window_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "member_count": len(members),
        "events": [dict(r) for r in rows],
        "usage": dict(usage_rows) if usage_rows else {},
    }


def get_user_analytics(user_id: str, days: int = 30) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT event_type, COUNT(*) as count, MIN(created_at) as first_seen, MAX(created_at) as last_seen
            FROM analytics_events
            WHERE created_at >= ? AND user_id = ?
            GROUP BY event_type
            ORDER BY count DESC
            """,
            (cutoff, user_id),
        ).fetchall()

        usage_rows = conn.execute(
            """
            SELECT SUM(tokens) as total_tokens, SUM(cost) as total_cost, COUNT(*) as total_requests,
            SUM(cached) as cached_requests
            FROM usage
            WHERE created_at >= ? AND user_id = ?
            """,
            (cutoff, user_id),
        ).fetchone()

    return {
        "user_id": user_id,
        "window_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "events": [dict(r) for r in rows],
        "usage": dict(usage_rows) if usage_rows else {},
    }


def export_analytics_csv(data: dict, filename: str = "analytics.csv") -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])

    if "usage" in data and data["usage"]:
        for key, value in data["usage"].items():
            writer.writerow([key, value])

    if "events" in data:
        writer.writerow(["event_type", "count", "first_seen", "last_seen"])
        for event in data["events"]:
            writer.writerow([
                event.get("event_type", ""),
                event.get("count", 0),
                event.get("first_seen", ""),
                event.get("last_seen", ""),
            ])

    output.seek(0)
    return output.getvalue()


def export_analytics_json(data: dict) -> str:
    return json.dumps(data, default=str, indent=2)


def get_realtime_dashboard(org_id: str) -> dict:
    members = _get_org_members(org_id)
    now = datetime.now(timezone.utc)
    last_hour = (now - timedelta(hours=1)).isoformat()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    with get_db() as conn:
        recent_rows = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM analytics_events
            WHERE created_at >= ? AND user_id IN ({})
            """.format(",".join("?" * len(members))),
            [last_hour] + members,
        ).fetchone()

        today_rows = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM analytics_events
            WHERE created_at >= ? AND user_id IN ({})
            """.format(",".join("?" * len(members))),
            [today] + members,
        ).fetchone()

        cost_rows = conn.execute(
            """
            SELECT SUM(cost) as total_cost FROM usage
            WHERE created_at >= ? AND user_id IN ({})
            """.format(",".join("?" * len(members))),
            [today] + members,
        ).fetchone()

    return {
        "org_id": org_id,
        "realtime_events_last_hour": recent_rows["cnt"] if recent_rows else 0,
        "events_today": today_rows["cnt"] if today_rows else 0,
        "cost_today": float(cost_rows["total_cost"] or 0) if cost_rows else 0.0,
        "generated_at": now.isoformat(),
    }
