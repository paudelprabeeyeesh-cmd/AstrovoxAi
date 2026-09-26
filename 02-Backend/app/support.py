import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List
from dataclasses import dataclass, field

from database.database import get_db

logger = logging.getLogger(__name__)


@dataclass
class SupportTicket:
    id: str
    tenant_id: Optional[str]
    user_id: str
    subject: str
    description: str
    priority: str = "medium"
    status: str = "open"
    category: str = "general"
    assigned_to: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None


@dataclass
class TicketComment:
    id: str
    ticket_id: str
    user_id: str
    comment: str
    is_internal: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HelpArticle:
    id: str
    slug: str
    title: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    views: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HelpCategory:
    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    sort_order: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SupportAgent:
    id: str
    user_id: str
    name: str
    email: str
    role: str = "agent"
    team: str = "support"
    is_online: bool = False
    max_tickets: int = 10
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ContextualHelp:
    id: str
    page: str
    element_selector: Optional[str]
    title: str
    content: str
    trigger: str = "on_view"
    sort_order: int = 0
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SupportTicketService:
    def __init__(self):
        self.tickets: Dict[str, SupportTicket] = {}

    def create_ticket(self, user_id: str, subject: str, description: str, priority: str = "medium", category: str = "general", tags: List[str] = None, tenant_id: Optional[str] = None) -> SupportTicket:
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
                    ticket.created_at,
                    ticket.updated_at,
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

    def list_tickets(self, user_id: str = None, status: str = None, assigned_to: str = None) -> List[SupportTicket]:
        tickets = list(self.tickets.values())
        if user_id:
            tickets = [t for t in tickets if t.user_id == user_id]
        if status:
            tickets = [t for t in tickets if t.status == status]
        if assigned_to:
            tickets = [t for t in tickets if t.assigned_to == assigned_to]
        return tickets

    def update_ticket(self, ticket_id: str, status: str = None, assigned_to: str = None, priority: str = None) -> Optional[SupportTicket]:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return None
        if status:
            ticket.status = status
            if status == "resolved":
                ticket.resolved_at = datetime.now(timezone.utc).isoformat()
        if assigned_to:
            ticket.assigned_to = assigned_to
        if priority:
            ticket.priority = priority
        ticket.updated_at = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                "UPDATE support_tickets SET status = ?, assigned_to = ?, priority = ?, updated_at = ?, resolved_at = ? WHERE id = ?",
                (ticket.status, ticket.assigned_to, ticket.priority, ticket.updated_at, ticket.resolved_at, ticket.id),
            )
            conn.commit()
        return ticket

    def add_comment(self, ticket_id: str, user_id: str, comment: str, is_internal: bool = False) -> TicketComment:
        comment_id = str(uuid.uuid4())
        ticket_comment = TicketComment(
            id=comment_id,
            ticket_id=ticket_id,
            user_id=user_id,
            comment=comment,
            is_internal=is_internal,
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO ticket_comments (id, ticket_id, user_id, comment, is_internal, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (comment_id, ticket_id, user_id, comment, 1 if is_internal else 0, ticket_comment.created_at),
            )
            conn.commit()
        return ticket_comment

    def get_comments(self, ticket_id: str) -> List[TicketComment]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, ticket_id, user_id, comment, is_internal, created_at FROM ticket_comments WHERE ticket_id = ? ORDER BY created_at ASC",
                (ticket_id,),
            ).fetchall()
            return [
                TicketComment(
                    id=row["id"],
                    ticket_id=row["ticket_id"],
                    user_id=row["user_id"],
                    comment=row["comment"],
                    is_internal=bool(row["is_internal"]),
                    created_at=row["created_at"],
                )
                for row in rows
            ]


class HelpCenterService:
    def create_article(self, slug: str, title: str, content: str, category: str, tags: List[str] = None) -> HelpArticle:
        article_id = str(uuid.uuid4())
        article = HelpArticle(
            id=article_id,
            slug=slug,
            title=title,
            content=content,
            category=category,
            tags=tags or [],
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO help_articles (id, slug, title, content, category, tags, views, helpful_count, not_helpful_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (article.id, article.slug, article.title, article.content, article.category, json.dumps(article.tags), article.views, article.helpful_count, article.not_helpful_count, article.created_at, article.updated_at),
            )
            conn.commit()
        return article

    def get_article(self, slug: str) -> Optional[HelpArticle]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM help_articles WHERE slug = ?", (slug,)).fetchone()
            if row:
                return HelpArticle(
                    id=row["id"],
                    slug=row["slug"],
                    title=row["title"],
                    content=row["content"],
                    category=row["category"],
                    tags=json.loads(row["tags"] or "[]"),
                    views=row["views"],
                    helpful_count=row["helpful_count"],
                    not_helpful_count=row["not_helpful_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
        return None

    def list_articles(self, category: str = None, limit: int = 50) -> List[HelpArticle]:
        with get_db() as conn:
            query = "SELECT * FROM help_articles"
            params = []
            if category:
                query += " WHERE category = ?"
                params.append(category)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [
                HelpArticle(
                    id=row["id"],
                    slug=row["slug"],
                    title=row["title"],
                    content=row["content"],
                    category=row["category"],
                    tags=json.loads(row["tags"] or "[]"),
                    views=row["views"],
                    helpful_count=row["helpful_count"],
                    not_helpful_count=row["not_helpful_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def increment_views(self, slug: str) -> None:
        with get_db() as conn:
            conn.execute("UPDATE help_articles SET views = views + 1 WHERE slug = ?", (slug,))
            conn.commit()

    def record_feedback(self, slug: str, helpful: bool) -> None:
        column = "helpful_count" if helpful else "not_helpful_count"
        with get_db() as conn:
            conn.execute(f"UPDATE help_articles SET {column} = {column} + 1 WHERE slug = ?", (slug,))
            conn.commit()

    def create_category(self, name: str, description: str = None, parent_id: str = None, sort_order: int = 0) -> HelpCategory:
        category_id = str(uuid.uuid4())
        category = HelpCategory(
            id=category_id,
            name=name,
            description=description,
            parent_id=parent_id,
            sort_order=sort_order,
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO help_categories (id, name, description, parent_id, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (category.id, category.name, category.description, category.parent_id, category.sort_order, category.created_at),
            )
            conn.commit()
        return category

    def list_categories(self) -> List[HelpCategory]:
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM help_categories ORDER BY sort_order ASC, name ASC").fetchall()
            return [
                HelpCategory(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    parent_id=row["parent_id"],
                    sort_order=row["sort_order"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]


class SupportAgentService:
    def create_agent(self, user_id: str, name: str, email: str, role: str = "agent", team: str = "support", max_tickets: int = 10) -> SupportAgent:
        agent_id = str(uuid.uuid4())
        agent = SupportAgent(
            id=agent_id,
            user_id=user_id,
            name=name,
            email=email,
            role=role,
            team=team,
            max_tickets=max_tickets,
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO support_agents (id, user_id, name, email, role, team, is_online, max_tickets, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (agent.id, agent.user_id, agent.name, agent.email, agent.role, agent.team, 1 if agent.is_online else 0, agent.max_tickets, agent.created_at),
            )
            conn.commit()
        return agent

    def get_agent(self, user_id: str) -> Optional[SupportAgent]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM support_agents WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return SupportAgent(
                    id=row["id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    email=row["email"],
                    role=row["role"],
                    team=row["team"],
                    is_online=bool(row["is_online"]),
                    max_tickets=row["max_tickets"],
                    created_at=row["created_at"],
                )
        return None

    def list_agents(self, team: str = None) -> List[SupportAgent]:
        with get_db() as conn:
            query = "SELECT * FROM support_agents"
            params = []
            if team:
                query += " WHERE team = ?"
                params.append(team)
            rows = conn.execute(query, params).fetchall()
            return [
                SupportAgent(
                    id=row["id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    email=row["email"],
                    role=row["role"],
                    team=row["team"],
                    is_online=bool(row["is_online"]),
                    max_tickets=row["max_tickets"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def set_online_status(self, user_id: str, is_online: bool) -> None:
        with get_db() as conn:
            conn.execute("UPDATE support_agents SET is_online = ? WHERE user_id = ?", (1 if is_online else 0, user_id))
            conn.commit()

    def get_available_agent(self, category: str = None) -> Optional[SupportAgent]:
        with get_db() as conn:
            query = "SELECT * FROM support_agents WHERE is_online = 1 AND (SELECT COUNT(*) FROM support_tickets WHERE assigned_to = support_agents.user_id AND status IN ('open', 'assigned')) < max_tickets"
            params = []
            if category:
                query += " AND team = ?"
                params.append(self._team_for_category(category))
            query += " ORDER BY RANDOM() LIMIT 1"
            row = conn.execute(query, params).fetchone()
            if row:
                return SupportAgent(
                    id=row["id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    email=row["email"],
                    role=row["role"],
                    team=row["team"],
                    is_online=bool(row["is_online"]),
                    max_tickets=row["max_tickets"],
                    created_at=row["created_at"],
                )
        return None

    def _team_for_category(self, category: str) -> str:
        routing_rules = {
            "billing": "billing-team",
            "technical": "engineering-team",
            "access": "security-team",
        }
        return routing_rules.get(category, "support-team")


class ContextualHelpService:
    def create_help_item(self, page: str, title: str, content: str, element_selector: str = None, trigger: str = "on_view", sort_order: int = 0) -> ContextualHelp:
        help_id = str(uuid.uuid4())
        help_item = ContextualHelp(
            id=help_id,
            page=page,
            element_selector=element_selector,
            title=title,
            content=content,
            trigger=trigger,
            sort_order=sort_order,
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO contextual_help (id, page, element_selector, title, content, trigger, sort_order, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (help_id, help_item.page, help_item.element_selector, help_item.title, help_item.content, help_item.trigger, help_item.sort_order, 1 if help_item.is_active else 0, help_item.created_at),
            )
            conn.commit()
        return help_item

    def get_help_for_page(self, page: str) -> List[ContextualHelp]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM contextual_help WHERE page = ? AND is_active = 1 ORDER BY sort_order ASC",
                (page,),
            ).fetchall()
            return [
                ContextualHelp(
                    id=row["id"],
                    page=row["page"],
                    element_selector=row["element_selector"],
                    title=row["title"],
                    content=row["content"],
                    trigger=row["trigger"],
                    sort_order=row["sort_order"],
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def list_all(self) -> List[ContextualHelp]:
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM contextual_help ORDER BY page ASC, sort_order ASC").fetchall()
            return [
                ContextualHelp(
                    id=row["id"],
                    page=row["page"],
                    element_selector=row["element_selector"],
                    title=row["title"],
                    content=row["content"],
                    trigger=row["trigger"],
                    sort_order=row["sort_order"],
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                )
                for row in rows
            ]


support_ticket_service = SupportTicketService()
help_center_service = HelpCenterService()
support_agent_service = SupportAgentService()
contextual_help_service = ContextualHelpService()
