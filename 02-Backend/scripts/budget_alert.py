#!/usr/bin/env python3
import os
import sys
import csv
import smtplib
from email.mime.text import MIMEText
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.metrics import get_daily_cost

DAILY_BUDGET_USD = float(os.getenv("DAILY_BUDGET_USD", "10.0"))
WEBHOOK_URL = os.getenv("ALERT_WEBHOOK", "")

def alert_if_needed():
    data = get_daily_cost(days=1)
    if not data:
        return
    cost = data[0]["cost"]
    if cost > DAILY_BUDGET_USD * 0.8:
        body = f"Budget alert: ${cost:.4f} spent today (limit ${DAILY_BUDGET_USD})"
        if WEBHOOK_URL:
            import urllib.request
            req = urllib.request.Request(WEBHOOK_URL, data=body.encode(), method="POST")
            urllib.request.urlopen(req)
        else:
            print(body)

if __name__ == "__main__":
    alert_if_needed()
