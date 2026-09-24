
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from .auth import get_current_user
from ..white_label import (
    create_white_label_config,
    get_white_label_config,
    update_white_label_config,
    delete_white_label_config,
)
from ..audit import log_action

router = APIRouter(prefix="/white-label", tags=["white-label"])


class WhiteLabelUpdate(BaseModel):
    brand_name: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    custom_css: Optional[str] = None
    email_from_name: Optional[str] = None
    email_from_address: Optional[str] = None
    support_email: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    terms_of_service_url: Optional[str] = None
    hide_powered_by: Optional[bool] = None


@router.post("/config")
def set_white_label(org_id: str = Query(...), payload: Optional[WhiteLabelUpdate] = None, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    kwargs = payload.model_dump(exclude_none=True) if payload else {}
    result = create_white_label_config(org_id, **kwargs)
    return result


@router.get("/config")
def get_config(org_id: str = Query(...)):
    config = get_white_label_config(org_id)
    if not config:
        raise HTTPException(status_code=404, detail="White-label config not found")
    return config


@router.put("/config")
def update_config(org_id: str = Query(...), payload: WhiteLabelUpdate = ...):
    kwargs = payload.model_dump(exclude_none=True)
    result = update_white_label_config(org_id, **kwargs)
    return result


@router.delete("/config")
def remove_config(org_id: str = Query(...), authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    success = delete_white_label_config(org_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"ok": True}
