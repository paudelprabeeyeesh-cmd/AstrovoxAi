"""ABAC policy management APIs."""

from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from utils.auth.auth_utils import get_user_id_from_token
from ..enterprise.abac import abac
from ..enterprise.models import ORG_ROLES, WORKSPACE_ROLES

router = APIRouter(prefix="/api/enterprise/abac", tags=["enterprise-abac"])


class ABACPolicyRequest(BaseModel):
    name: str
    effect: str
    conditions: Dict[str, Any]


class ABACEvaluateRequest(BaseModel):
    user_id: str
    organization_id: str = ""
    workspace_id: str = ""
    resource_type: str = ""
    resource_id: str = ""
    action: str = ""
    attributes: Optional[List[Dict[str, Any]]] = None


@router.post("/policies")
async def create_abac_policy(request: ABACPolicyRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    abac.add_policy({
        "name": request.name,
        "effect": request.effect,
        "conditions": request.conditions,
    })
    return {"status": "OK", "message": "ABAC policy added", "name": request.name}


@router.get("/policies")
async def list_abac_policies(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "policies": abac._policies}


@router.post("/evaluate")
async def evaluate_abac(request: ABACEvaluateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    from ..enterprise.abac import ABACAttribute, ABACContext
    context = ABACContext(
        user_id=request.user_id,
        organization_id=request.organization_id,
        workspace_id=request.workspace_id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        action=request.action,
        attributes=[
            ABACAttribute(key=a["key"], value=a["value"], source=a.get("source", "static"))
            for a in (request.attributes or [])
        ],
    )
    allowed = abac.evaluate(context)
    return {"status": "OK", "allowed": allowed}


@router.get("/permissions/check")
async def check_permission(user_id: str, organization_id: str, permission: str, authorization: str = Header(None)):
    auth_user_id = get_user_id_from_token(authorization)
    has_perm = abac.has_org_permission(user_id, organization_id, permission)
    return {"status": "OK", "user_id": user_id, "organization_id": organization_id, "permission": permission, "allowed": has_perm}


@router.get("/roles/organization")
async def list_org_roles(authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "roles": [
            {"name": name, "description": data["description"], "permissions": data["permissions"]}
            for name, data in ORG_ROLES.items()
        ],
    }


@router.get("/roles/workspace")
async def list_workspace_roles(authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "roles": [
            {"name": name, "description": data["description"], "permissions": data["permissions"]}
            for name, data in WORKSPACE_ROLES.items()
        ],
    }
