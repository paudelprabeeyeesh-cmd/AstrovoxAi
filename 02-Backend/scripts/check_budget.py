import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.metrics import get_daily_cost
from app.subscriptions import get_plan_limits

DAILY_BUDGET_USD = float(os.getenv("DAILY_BUDGET_USD", "10.0"))

def check_budget():
    data = get_daily_cost(days=7)
    today = data[0] if data else {"cost": 0, "requests": 0}
    avg = sum(d["cost"] for d in data[1:]) / 6 if len(data) > 1 else 0
    projected = avg * 30
    print(f"Today: ${today['cost']:.4f} ({today['requests']} requests)")
    print(f"7-day avg: ${avg:.4f}")
    print(f"Projected month-end: ${projected:.2f}")
    if today["cost"] > DAILY_BUDGET_USD * 0.8:
        print(f"ALERT: {today['cost']:.4f} > 80% of daily budget ${DAILY_BUDGET_USD}")
    else:
        print(f"OK: under {DAILY_BUDGET_USD}")
