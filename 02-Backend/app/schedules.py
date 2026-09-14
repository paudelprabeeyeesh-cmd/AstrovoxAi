import smtplib
import uuid
from datetime import datetime
from email.mime.text import MIMEText

from apscheduler.schedulers.background import BackgroundScheduler

from .database import get_db
from .schemas import ScheduleCreate, ScheduleOut
from .templates import get_template

scheduler = BackgroundScheduler()
scheduler.start()


def send_email(to_addr: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "astrovox@example.com"
    msg["To"] = to_addr
    try:
        with smtplib.SMTP("localhost", 25) as server:
            server.send_message(msg)
    except Exception:
        pass


def run_schedule(schedule_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, template_id, email FROM schedules WHERE id = ?",
            (schedule_id,),
        ).fetchone()
        if not row:
            return
        user_id, template_id, email = row["user_id"], row["template_id"], row["email"]
        prompt = "Daily summary"
        if template_id:
            tpl = get_template(template_id, user_id)
            prompt = tpl.prompt
        send_email(email, "AstrovoxAI Daily", f"Result for {user_id}:\n\n{prompt}")
        conn.execute(
            "UPDATE schedules SET last_run = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), schedule_id),
        )
        conn.commit()


def create_schedule(user_id: str, data: ScheduleCreate) -> ScheduleOut:
    schedule_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO schedules (id, user_id, template_id, cron, email) VALUES (?, ?, ?, ?, ?)",
            (schedule_id, user_id, data.template_id, data.cron, data.email),
        )
        conn.commit()
    try:
        scheduler.add_job(
            run_schedule,
            "cron",
            id=schedule_id,
            args=[schedule_id],
            **parse_cron(data.cron),
        )
    except Exception:
        pass
    return get_schedule(schedule_id, user_id)


def get_schedule(schedule_id: str, user_id: str) -> ScheduleOut:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, template_id, cron, email, last_run, active, created_at FROM schedules WHERE id = ? AND user_id = ?",
            (schedule_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Schedule not found")
        return ScheduleOut(
            id=row["id"],
            template_id=row["template_id"],
            cron=row["cron"],
            email=row["email"],
            last_run=(
                datetime.fromisoformat(row["last_run"]) if row["last_run"] else None
            ),
            active=bool(row["active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_schedules(user_id: str) -> list[ScheduleOut]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, template_id, cron, email, last_run, active, created_at FROM schedules WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [
            ScheduleOut(
                id=r["id"],
                template_id=r["template_id"],
                cron=r["cron"],
                email=r["email"],
                last_run=(
                    datetime.fromisoformat(r["last_run"]) if r["last_run"] else None
                ),
                active=bool(r["active"]),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def delete_schedule(schedule_id: str, user_id: str):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM schedules WHERE id = ? AND user_id = ?", (schedule_id, user_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError("Schedule not found")
    try:
        scheduler.remove_job(schedule_id)
    except Exception:
        pass


def parse_cron(cron: str) -> dict:
    parts = cron.strip().split()
    if len(parts) != 5:
        return {"hour": "9", "minute": "0"}
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }
