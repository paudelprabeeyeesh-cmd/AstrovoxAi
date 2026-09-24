
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/usage", tags=["usage"])


class QuotaCreate(BaseModel):
    resource_type: str
    limit_value: float
    period: str = "monthly"


class UsageRecord(BaseModel):
    resource_type: str
    quantity: float
    unit: str = "count"
    cost: float = 0.0


@router.post("/organizations/{org_id}/quotas")
def create_quota(org_id: str, payload: QuotaCreate, user_id: Optional[str] = None):
    from ..quota_management import create_quota
    return create_quota(org_id, payload.resource_type, payload.limit_value, payload.period, user_id)


@router.get("/organizations/{org_id}/quotas")
def list_quotas(org_id: str):
    from ..quota_management import list_quotas
    return list_quotas(org_id)


@router.get("/organizations/{org_id}/quotas/{resource_type}")
def check_quota(org_id: str, resource_type: str, quantity: float = Query(0), user_id: Optional[str] = None):
    from ..quota_management import check_quota
    return check_quota(org_id, resource_type, quantity, user_id)


@router.post("/organizations/{org_id}/usage")
def record_usage(org_id: str, payload: UsageRecord, user_id: Optional[str] = None, billing_period: Optional[str] = None):
    from ..quota_management import record_usage
    return record_usage(org_id, user_id, payload.resource_type, payload.quantity, payload.unit, payload.cost, billing_period)


@router.get("/organizations/{org_id}/usage/summary")
def usage_summary(org_id: str, billing_period: Optional[str] = None):
    from ..quota_management import get_usage_summary
    return get_usage_summary(org_id, billing_period)


@router.post("/organizations/{org_id}/quotas/reset")
def reset_quotas(org_id: str, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    from ..quota_management import reset_quotas
    return reset_quotas(org_id, user_id)
