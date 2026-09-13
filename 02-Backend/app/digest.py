import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

def send_daily_digest(user_email: str, user_id: str, yesterday_actions: list, pending: list, suggestion: str):
    body = f"""Hi there,

Here is your daily digest from AstrovoxAI.

Yesterday ({datetime.utcnow().date() - timedelta(days=1)}):
"""
    for action in yesterday_actions[:5]:
        body += f"- {action}\n"
    body += "\nPending:\n"
    for item in pending[:5]:
        body += f"- {item}\n"
    body += f"\nSuggestion:\n{suggestion}\n\nThanks for using AstrovoxAI."
    msg = MIMEText(body)
    msg["Subject"] = "Your AstrovoxAI Daily Digest"
    msg["From"] = "astrovox@example.com"
    msg["To"] = user_email
    try:
        with smtplib.SMTP("localhost", 25) as server:
            server.send_message(msg)
    except Exception:
        pass
