
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/scim", tags=["scim"])


class SCIMUser(BaseModel):
    schemas: List[str]
    userName: str
    emails: List[dict]
    displayName: Optional[str] = None
    active: bool = True


class SCIMGroup(BaseModel):
    schemas: List[str]
    displayName: str
    members: List[dict] = []


@router.post("/organizations/{org_id}/Users")
def scim_provision_user(org_id: str, payload: SCIMUser):
    from ..sso import sso_service
    scim_data = {
        "emails": payload.emails,
        "display_name": payload.displayName,
        "active": payload.active,
    }
    result = sso_service.provision_scim_user(org_id, scim_data)
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Response"],
        "id": result["user_id"],
        "userName": payload.userName,
        "emails": payload.emails,
        "active": payload.active,
        "meta": {"resourceType": "User"},
    }


@router.get("/organizations/{org_id}/Users")
def scim_list_users(org_id: str, count: int = Query(10, ge=1, le=100), startIndex: int = Query(1, ge=1)):
    from ..database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, email FROM users WHERE id IN (SELECT user_id FROM sso_users WHERE org_id = ?) LIMIT ? OFFSET ?",
            (org_id, count, startIndex - 1),
        ).fetchall()
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(rows),
        "Resources": [{"id": r["id"], "userName": r["email"], "emails": [{"value": r["email"]}]} for r in rows],
    }


@router.get("/organizations/{org_id}/Users/{user_id}")
def scim_get_user(org_id: str, user_id: str):
    from ..database import get_db
    with get_db() as conn:
        row = conn.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": row["id"],
        "userName": row["email"],
        "emails": [{"value": row["email"]}],
    }


@router.delete("/organizations/{org_id}/Users/{user_id}")
def scim_deprovision_user(org_id: str, user_id: str):
    from ..sso import sso_service
    result = sso_service.deprovision_scim_user(org_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return {}


@router.patch("/organizations/{org_id}/Users/{user_id}")
def scim_update_user(org_id: str, user_id: str, payload: SCIMUser):
    from ..database import get_db
    with get_db() as conn:
        conn.execute("UPDATE users SET email = ? WHERE id = ?", (payload.userName, user_id))
        conn.commit()
    return scim_get_user(org_id, user_id)



