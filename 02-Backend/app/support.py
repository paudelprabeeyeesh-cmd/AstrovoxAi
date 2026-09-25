import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class SupportTicket:
    id: str
    tenant_id: str
    user_id: str
    subject: str
    description: str
    priority: str = "medium"
    status: str = "open"
    category: str = "general"
    assigned_to: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=datetime.now(timezone.utc).timestamp)
    updated_at: float = field(default_factory=datetime.now(timezone.utc).timestamp)
    resolved_at: Optional[float] = None


class SupportTicketService:
    def __init__(self):
        self.tickets: Dict[str, SupportTicket] = {}

    def create_ticket(self, tenant_id: str, user_id: str, subject: str, description: str, priority: str = "medium", category: str = "general", tags: List[str] = None) -> SupportTicket:
        ticket_id = str(uuid.uuid4())
        ticket = SupportTicket(
            id=ticket_id,
            tenant_id=tenant_id,
            user_id=user_id,
            subject=subject,
            description=description,
            priority=priority,
            category=category,
            tags=tags or [],
        )
        self.tickets[ticket_id] = ticket
        self._persist(ticket)
        self._auto_route(ticket)
        return ticket

    def _persist(self, ticket: SupportTicket) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO support_tickets (id, tenant_id, user_id, subject, description, priority, status, category, assigned_to, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ticket.id,
                    ticket.tenant_id,
                    ticket.user_id,
                    ticket.subject,
                    ticket.description,
                    ticket.priority,
                    ticket.status,
                    ticket.category,
                    ticket.assigned_to,
                    json.dumps(ticket.tags),
                    datetime.fromtimestamp(ticket.created_at, tz=timezone.utc).isoformat(),
                    datetime.fromtimestamp(ticket.updated_at, tz=timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def _auto_route(self, ticket: SupportTicket) -> None:
        routing_rules = {
            "billing": "billing-team",
            "technical": "engineering-team",
            "access": "security-team",
            "general": "support-team",
        }
        team = routing_rules.get(ticket.category, "support-team")
        ticket.assigned_to = team
        ticket.status = "assigned"
        with get_db() as conn:
            conn.execute(
                "UPDATE support_tickets SET assigned_to = ?, status = ? WHERE id = ?",
                (team, ticket.status, ticket.id),
            )
            conn.commit()
        logger.info("Auto-routed ticket %s to %s", ticket.id, team)

    def get_ticket(self, ticket_id: str) -> Optional[SupportTicket]:
        return self.tickets.get(ticket_id)

    def list_tickets(self, tenant_id: str = None, status: str = None) -> List[SupportTicket]:
        tickets = list(self.tickets.values())
        if tenant_id:
            tickets = [t for t in tickets if t.tenant_id == tenant_id]
        if status:
            tickets = [t for t in tickets if t.status == status]
        return tickets

    def update_ticket(self, ticket_id: str, status: str = None, assigned_to: str = None) -> Optional[SupportTicket]:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return None
        if status:
            ticket.status = status
            if status == "resolved":
                ticket.resolved_at = datetime.now(timezone.utc).timestamp()
        if assigned_to:
            ticket.assigned_to = assigned_to
        ticket.updated_at = datetime.now(timezone.utc).timestamp()
        with get_db() as conn:
            conn.execute(
                "UPDATE support_tickets SET status = ?, assigned_to = ?, updated_at = ?, resolved_at = ? WHERE id = ?",
                (ticket.status, ticket.assigned_to, datetime.fromtimestamp(ticket.updated_at, tz=timezone.utc).isoformat(), datetime.fromtimestamp(ticket.resolved_at, tz=timezone.utc).isoformat() if ticket.resolved_at else None, ticket.id),
            )
            conn.commit()
        return ticket


support_ticket_service = SupportTicketService()
