from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


def require_admin(authorization: Optional[str] = Header(None)):
    if not authorization or "admin" not in authorization.lower():
        raise HTTPException(status_code=403, detail="Admin role required")
    return authorization


class UserResponse(BaseModel):
    id: str
    email: str
    plan: str


class StatsResponse(BaseModel):
    users: int
    pro: int
    team: int


users_store: dict[str, dict] = {}


@router.get("/users", response_model=List[UserResponse])
async def list_users(_admin: str = Depends(require_admin)):
    return list(users_store.values())


@router.get("/stats", response_model=StatsResponse)
async def stats(_admin: str = Depends(require_admin)):
    users = list(users_store.values())
    return StatsResponse(
        users=len(users),
        pro=sum(1 for u in users if u.get("plan") == "pro"),
        team=sum(1 for u in users if u.get("plan") == "team"),
    )
