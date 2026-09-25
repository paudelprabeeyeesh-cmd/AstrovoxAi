"""Support ticket routing APIs."""

from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from utils.auth.auth_utils import get_user_id_from_token
from .ticket_routing import support_router

router = APIRouter(prefix="/api/enterprise/support", tags=["enterprise-support"])


class RouteTicketRequest(BaseModel):
    ticket_id: str
    category: str
    priority: str
    description: Optional[str] = ""


class AddRoutingRuleRequest(BaseModel):
    name: str
    category: str
    priority: str
    team: str
    sla_hours: int


class EscalateTicketRequest(BaseModel):
    ticket_id: str
    reason: str


@router.post("/route")
async def route_ticket(request: RouteTicketRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    assignment = support_router.route_ticket(request.ticket_id, request.category, request.priority, request.description or "")
    return {
        "status": "OK",
        "assignment": {
            "assignment_id": assignment.assignment_id,
            "ticket_id": assignment.ticket_id,
            "team": assignment.team,
            "assigned_to": assignment.assigned_to,
            "reason": assignment.reason,
        },
    }


@router.get("/routing-rules")
async def list_routing_rules(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    rules = support_router.list_rules()
    return {"status": "OK", "rules": rules}


@router.post("/routing-rules")
async def add_routing_rule(request: AddRoutingRuleRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    rule = support_router.add_rule(request.name, request.category, request.priority, request.team, request.sla_hours)
    return {
        "status": "OK",
        "rule": {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "category": rule.category,
            "priority": rule.priority,
            "team": rule.team,
            "sla_hours": rule.sla_hours,
        },
    }


@router.post("/escalate")
async def escalate_ticket(request: EscalateTicketRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    assignment = support_router.escalate_ticket(request.ticket_id, request.reason)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return {
        "status": "OK",
        "assignment": {
            "assignment_id": assignment.assignment_id,
            "ticket_id": assignment.ticket_id,
            "team": assignment.team,
            "reason": assignment.reason,
        },
    }
