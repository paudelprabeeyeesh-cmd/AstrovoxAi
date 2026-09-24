
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from .database import get_db
from .audit import log_action


def create_support_ticket(org_id: str, user_id: Optional[str], subject: str, description: str, priority: str = "medium", category: Optional[str] = None) -> dict:
    ticket_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    ticket_number = f"TKT-{now[:10].replace('-', '')}-{ticket_id[:8].upper()}"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO support_tickets (id, org_id, user_id, ticket_number, subject, description, priority, category, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, org_id, user_id, ticket_number, subject, description, priority, category, "open", now, now),
        )
        conn.commit()
    log_action(user_id, "create_support_ticket", f"ticket:{ticket_id}", {"priority": priority, "category": category})
    return {"id": ticket_id, "ticket_number": ticket_number, "subject": subject, "priority": priority, "status": "open"}


def get_support_ticket(ticket_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None


def list_support_tickets(org_id: str, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[dict]:
    with get_db() as conn:
        query = "SELECT * FROM support_tickets WHERE org_id = ?"
        params = [org_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_support_ticket(ticket_id: str, status: Optional[str] = None, priority: Optional[str] = None, assigned_to: Optional[str] = None, tags: Optional[str] = None) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)).fetchone()
        if not row:
            raise ValueError("Ticket not found")
        updates = {}
        if status:
            updates["status"] = status
            if status in ("resolved", "closed"):
                updates["resolved_at"] = datetime.now(timezone.utc).isoformat()
        if priority:
            updates["priority"] = priority
        if assigned_to:
            updates["assigned_to"] = assigned_to
        if tags is not None:
            updates["tags"] = tags
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [ticket_id]
        conn.execute(f"UPDATE support_tickets SET {set_clause} WHERE id = ?", values)
        conn.commit()
    return get_support_ticket(ticket_id)


def add_ticket_message(ticket_id: str, user_id: Optional[str], message: str, message_type: str = "reply", attachments: Optional[str] = None) -> dict:
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO support_ticket_messages (id, ticket_id, user_id, message, message_type, attachments, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg_id, ticket_id, user_id, message, message_type, attachments, now),
        )
        conn.execute("UPDATE support_tickets SET updated_at = ? WHERE id = ?", (now, ticket_id))
        conn.commit()
    return {"id": msg_id, "ticket_id": ticket_id, "message": message, "message_type": message_type}


def get_ticket_messages(ticket_id: str) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM support_ticket_messages WHERE ticket_id = ? ORDER BY created_at ASC", (ticket_id,)).fetchall()
        return [dict(r) for r in rows]


def delete_support_ticket(ticket_id: str, requester_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM support_tickets WHERE id = ?", (ticket_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    if deleted:
        log_action(requester_id, "delete_support_ticket", f"ticket:{ticket_id}", {})
    return deleted


def get_ticket_stats(org_id: str) -> dict:
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM support_tickets WHERE org_id = ?", (org_id,)).fetchone()["c"]
        open_tickets = conn.execute("SELECT COUNT(*) as c FROM support_tickets WHERE org_id = ? AND status = 'open'", (org_id,)).fetchone()["c"]
        avg_resolution = conn.execute("SELECT AVG(julianday(resolved_at) - julianday(created_at)) as avg FROM support_tickets WHERE org_id = ? AND resolved_at IS NOT NULL", (org_id,)).fetchone()
        avg_days = round(avg_resolution["avg"], 2) if avg_resolution and avg_resolution["avg"] else 0
        return {"total": total, "open": open_tickets, "avg_resolution_days": avg_days}
