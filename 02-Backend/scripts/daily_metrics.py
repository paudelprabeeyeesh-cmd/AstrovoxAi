import csv
import os
from datetime import datetime, timedelta, timezone
from .database import get_db

def append_daily_metrics():
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    with get_db() as conn:
        users = conn.execute("SELECT COUNT(*) as c FROM users WHERE date(created_at) <= ?", (today.isoformat(),)).fetchone()["c"]
        active = conn.execute("SELECT COUNT(DISTINCT user_id) as c FROM usage WHERE date(created_at) = ?", (yesterday.isoformat(),)).fetchone()["c"]
        paid = conn.execute("SELECT COUNT(*) as c FROM subscriptions WHERE status = 'active'").fetchone()["c"]
        revenue_row = conn.execute("SELECT SUM(amount) as r FROM subscriptions WHERE status = 'active'").fetchone()
        revenue = revenue_row["r"] or 0.0
        cost_row = conn.execute("SELECT SUM(cost) as c FROM usage WHERE date(created_at) = ?", (yesterday.isoformat(),)).fetchone()
        cost = cost_row["c"] or 0.0
        margin = ((revenue - cost) / revenue * 100) if revenue > 0 else 0
    path = os.path.join(os.path.dirname(__file__), "..", "data", "daily_metrics.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "users", "active", "paid", "revenue", "cost", "margin"])
        writer.writerow([yesterday.isoformat(), users, active, paid, round(revenue, 2), round(cost, 4), round(margin, 1)])
