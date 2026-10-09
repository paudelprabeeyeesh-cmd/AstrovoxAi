
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

from .auth import get_current_user
from ..support_tickets import (
    create_support_ticket,
    get_support_ticket,
    list_support_tickets,
    update_support_ticket,
    add_ticket_message,
    get_ticket_messages,
    delete_support_ticket,
    get_ticket_stats,
)
from ..audit import log_action

router = APIRouter(prefix="/support", tags=["support"])


class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "medium"
    category: Optional[str] = None


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[str] = None


class MessageCreate(BaseModel):
    message: str
    message_type: str = "reply"


@router.post("/tickets")
def create_ticket(payload: TicketCreate, org_id: str = Query(...), authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    return create_support_ticket(org_id, user_id, payload.subject, payload.description, payload.priority, payload.category)


@router.get("/tickets")
def list_tickets(org_id: str = Query(...), status: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return list_support_tickets(org_id, status, limit, offset)


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    ticket = get_support_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.put("/tickets/{ticket_id}")
def update_ticket(ticket_id: str, payload: TicketUpdate):
    return update_support_ticket(ticket_id, payload.status, payload.priority, payload.assigned_to, payload.tags)


@router.post("/tickets/{ticket_id}/messages")
def add_message(ticket_id: str, payload: MessageCreate, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    return add_ticket_message(ticket_id, user_id, payload.message, payload.message_type)


@router.get("/tickets/{ticket_id}/messages")
def list_messages(ticket_id: str):
    return get_ticket_messages(ticket_id)


@router.delete("/tickets/{ticket_id}")
def delete_ticket(ticket_id: str, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    success = delete_support_ticket(ticket_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ok": True}


@router.get("/stats")
def ticket_stats(org_id: str = Query(...)):
    return get_ticket_stats(org_id)
