"""Customer experience and support API routes."""

from __future__ import annotations

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, status, Header, Query
from pydantic import BaseModel, Field

from app.utils.auth.auth_utils import get_user_id_from_token
from app.support import (
    support_ticket_service,
    help_center_service,
    support_agent_service,
    contextual_help_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/support", tags=["support"])


# ============================================================================
# Request / Response Models
# ============================================================================

class CreateTicketRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    category: str = Field(default="general", max_length=50)
    tags: List[str] = Field(default_factory=list)


class UpdateTicketRequest(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(open|assigned|in_progress|resolved|closed|reopened)$")
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high|critical)$")
    assigned_to: Optional[str] = None


class TicketCommentRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=5000)
    is_internal: bool = False


class CreateArticleRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list)


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    parent_id: Optional[str] = None
    sort_order: int = Field(default=0)


class ArticleFeedbackRequest(BaseModel):
    helpful: bool


class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="agent", max_length=50)
    team: str = Field(default="support", max_length=50)
    max_tickets: int = Field(default=10, ge=1, le=100)


class AgentStatusRequest(BaseModel):
    is_online: bool


class CreateContextualHelpRequest(BaseModel):
    page: str = Field(..., min_length=1, max_length=100)
    element_selector: Optional[str] = Field(default=None, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    trigger: str = Field(default="on_view", max_length=50)
    sort_order: int = Field(default=0)


# ============================================================================
# Support Tickets
# ============================================================================

@router.post("/tickets")
async def create_ticket(request: CreateTicketRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    ticket = support_ticket_service.create_ticket(
        user_id=user_id,
        subject=request.subject,
        description=request.description,
        priority=request.priority,
        category=request.category,
        tags=request.tags,
    )
    return {
        "status": "OK",
        "ticket": {
            "id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "priority": ticket.priority,
            "status": ticket.status,
            "category": ticket.category,
            "assigned_to": ticket.assigned_to,
            "tags": ticket.tags,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        },
    }


@router.get("/tickets")
async def list_tickets(
    authorization: str = Header(None),
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
):
    user_id = get_user_id_from_token(authorization)
    tickets = support_ticket_service.list_tickets(user_id=user_id, status=status, assigned_to=assigned_to)
    return {
        "status": "OK",
        "tickets": [
            {
                "id": t.id,
                "subject": t.subject,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
                "category": t.category,
                "assigned_to": t.assigned_to,
                "tags": t.tags,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "resolved_at": t.resolved_at,
            }
            for t in tickets
        ],
    }


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    ticket = support_ticket_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    comments = support_ticket_service.get_comments(ticket_id)
    return {
        "status": "OK",
        "ticket": {
            "id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "priority": ticket.priority,
            "status": ticket.status,
            "category": ticket.category,
            "assigned_to": ticket.assigned_to,
            "tags": ticket.tags,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "resolved_at": ticket.resolved_at,
        },
        "comments": [
            {
                "id": c.id,
                "ticket_id": c.ticket_id,
                "user_id": c.user_id,
                "comment": c.comment,
                "is_internal": c.is_internal,
                "created_at": c.created_at,
            }
            for c in comments
        ],
    }


@router.put("/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, request: UpdateTicketRequest, authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    ticket = support_ticket_service.update_ticket(
        ticket_id=ticket_id,
        status=request.status,
        assigned_to=request.assigned_to,
        priority=request.priority,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {
        "status": "OK",
        "ticket": {
            "id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "priority": ticket.priority,
            "status": ticket.status,
            "category": ticket.category,
            "assigned_to": ticket.assigned_to,
            "tags": ticket.tags,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "resolved_at": ticket.resolved_at,
        },
    }


@router.post("/tickets/{ticket_id}/comments")
async def add_ticket_comment(ticket_id: str, request: TicketCommentRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    ticket = support_ticket_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    comment = support_ticket_service.add_comment(ticket_id, user_id, request.comment, request.is_internal)
    return {
        "status": "OK",
        "comment": {
            "id": comment.id,
            "ticket_id": comment.ticket_id,
            "user_id": comment.user_id,
            "comment": comment.comment,
            "is_internal": comment.is_internal,
            "created_at": comment.created_at,
        },
    }


# ============================================================================
# Help Center
# ============================================================================

@router.post("/articles")
async def create_article(request: CreateArticleRequest, authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    article = help_center_service.create_article(
        slug=request.slug,
        title=request.title,
        content=request.content,
        category=request.category,
        tags=request.tags,
    )
    return {
        "status": "OK",
        "article": {
            "id": article.id,
            "slug": article.slug,
            "title": article.title,
            "content": article.content,
            "category": article.category,
            "tags": article.tags,
            "views": article.views,
            "helpful_count": article.helpful_count,
            "not_helpful_count": article.not_helpful_count,
            "created_at": article.created_at,
            "updated_at": article.updated_at,
        },
    }


@router.get("/articles")
async def list_articles(category: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=100)):
    articles = help_center_service.list_articles(category=category, limit=limit)
    return {
        "status": "OK",
        "articles": [
            {
                "id": a.id,
                "slug": a.slug,
                "title": a.title,
                "content": a.content,
                "category": a.category,
                "tags": a.tags,
                "views": a.views,
                "helpful_count": a.helpful_count,
                "not_helpful_count": a.not_helpful_count,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
            for a in articles
        ],
    }


@router.get("/articles/{slug}")
async def get_article(slug: str, authorization: Optional[str] = Header(None)):
    if authorization:
        get_user_id_from_token(authorization)
    article = help_center_service.get_article(slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    help_center_service.increment_views(slug)
    return {
        "status": "OK",
        "article": {
            "id": article.id,
            "slug": article.slug,
            "title": article.title,
            "content": article.content,
            "category": article.category,
            "tags": article.tags,
            "views": article.views + 1,
            "helpful_count": article.helpful_count,
            "not_helpful_count": article.not_helpful_count,
            "created_at": article.created_at,
            "updated_at": article.updated_at,
        },
    }


@router.post("/articles/{slug}/feedback")
async def article_feedback(slug: str, request: ArticleFeedbackRequest, authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    article = help_center_service.get_article(slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    help_center_service.record_feedback(slug, request.helpful)
    return {"status": "OK", "message": "Feedback recorded"}


@router.post("/categories")
async def create_category(request: CreateCategoryRequest, authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    category = help_center_service.create_category(
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
        sort_order=request.sort_order,
    )
    return {
        "status": "OK",
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "parent_id": category.parent_id,
            "sort_order": category.sort_order,
            "created_at": category.created_at,
        },
    }


@router.get("/categories")
async def list_categories():
    categories = help_center_service.list_categories()
    return {
        "status": "OK",
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "parent_id": c.parent_id,
                "sort_order": c.sort_order,
                "created_at": c.created_at,
            }
            for c in categories
        ],
    }


# ============================================================================
# Support Agents
# ============================================================================

@router.post("/agents")
async def create_agent(request: CreateAgentRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    agent = support_agent_service.create_agent(
        user_id=user_id,
        name=request.name,
        email=request.email,
        role=request.role,
        team=request.team,
        max_tickets=request.max_tickets,
    )
    return {
        "status": "OK",
        "agent": {
            "id": agent.id,
            "user_id": agent.user_id,
            "name": agent.name,
            "email": agent.email,
            "role": agent.role,
            "team": agent.team,
            "is_online": agent.is_online,
            "max_tickets": agent.max_tickets,
            "created_at": agent.created_at,
        },
    }


@router.get("/agents")
async def list_agents(team: Optional[str] = Query(None)):
    agents = support_agent_service.list_agents(team=team)
    return {
        "status": "OK",
        "agents": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "name": a.name,
                "email": a.email,
                "role": a.role,
                "team": a.team,
                "is_online": a.is_online,
                "max_tickets": a.max_tickets,
                "created_at": a.created_at,
            }
            for a in agents
        ],
    }


@router.get("/agents/me")
async def get_my_agent(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    agent = support_agent_service.get_agent(user_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    return {
        "status": "OK",
        "agent": {
            "id": agent.id,
            "user_id": agent.user_id,
            "name": agent.name,
            "email": agent.email,
            "role": agent.role,
            "team": agent.team,
            "is_online": agent.is_online,
            "max_tickets": agent.max_tickets,
            "created_at": agent.created_at,
        },
    }


@router.post("/agents/me/status")
async def set_agent_status(request: AgentStatusRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    support_agent_service.set_online_status(user_id, request.is_online)
    return {"status": "OK", "is_online": request.is_online}


# ============================================================================
# Contextual Help
# ============================================================================

@router.post("/contextual-help")
async def create_contextual_help(request: CreateContextualHelpRequest, authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    help_item = contextual_help_service.create_help_item(
        page=request.page,
        title=request.title,
        content=request.content,
        element_selector=request.element_selector,
        trigger=request.trigger,
        sort_order=request.sort_order,
    )
    return {
        "status": "OK",
        "help": {
            "id": help_item.id,
            "page": help_item.page,
            "element_selector": help_item.element_selector,
            "title": help_item.title,
            "content": help_item.content,
            "trigger": help_item.trigger,
            "sort_order": help_item.sort_order,
            "is_active": help_item.is_active,
            "created_at": help_item.created_at,
        },
    }


@router.get("/contextual-help/{page}")
async def get_contextual_help(page: str):
    items = contextual_help_service.get_help_for_page(page)
    return {
        "status": "OK",
        "help_items": [
            {
                "id": h.id,
                "page": h.page,
                "element_selector": h.element_selector,
                "title": h.title,
                "content": h.content,
                "trigger": h.trigger,
                "sort_order": h.sort_order,
                "is_active": h.is_active,
            }
            for h in items
        ],
    }


@router.get("/contextual-help")
async def list_contextual_help():
    items = contextual_help_service.list_all()
    return {
        "status": "OK",
        "help_items": [
            {
                "id": h.id,
                "page": h.page,
                "element_selector": h.element_selector,
                "title": h.title,
                "content": h.content,
                "trigger": h.trigger,
                "sort_order": h.sort_order,
                "is_active": h.is_active,
                "created_at": h.created_at,
            }
            for h in items
        ],
    }
