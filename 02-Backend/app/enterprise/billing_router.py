"""Enterprise billing metering and usage quotas APIs."""

from fastapi import APIRouter, HTTPException, status, Header, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.utils.auth.auth_utils import get_user_id_from_token
from ..billing_meter import billing_meter
from ..usage_quota import usage_quota_manager

router = APIRouter(prefix="/api/enterprise/billing", tags=["enterprise-billing"])


class MeterUsageRequest(BaseModel):
    tenant_id: str
    user_id: str
    resource_type: str
    quantity: float
    unit: str
    cost: float


class QuotaRequest(BaseModel):
    tenant_id: str
    user_id: str
    resource_type: str
    limit_value: float
    period: Optional[str] = "monthly"


@router.post("/meter")
async def meter_usage(request: MeterUsageRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    record = billing_meter.record_usage(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        resource_type=request.resource_type,
        quantity=request.quantity,
        unit=request.unit,
        cost=request.cost,
    )
    return {
        "status": "OK",
        "record": {
            "id": record.id,
            "tenant_id": record.tenant_id,
            "resource_type": record.resource_type,
            "quantity": record.quantity,
            "cost": record.cost,
            "created_at": record.created_at,
        },
    }


@router.get("/usage/{tenant_id}")
async def get_tenant_usage(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    usage = billing_meter.get_tenant_usage(tenant_id)
    return {"status": "OK", "tenant_id": tenant_id, "usage": usage}


@router.get("/usage/{tenant_id}/summary")
async def get_tenant_usage_summary(tenant_id: str, period: str = Query("monthly"), authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    summary = billing_meter.get_tenant_cost_summary(tenant_id, period)
    return {"status": "OK", "tenant_id": tenant_id, "period": period, "summary": summary}


@router.post("/quotas")
async def create_quota(request: QuotaRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    quota = usage_quota_manager.create_quota(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        resource_type=request.resource_type,
        limit_value=request.limit_value,
        period=request.period or "monthly",
    )
    return {
        "status": "OK",
        "quota": {
            "id": quota.id,
            "tenant_id": quota.tenant_id,
            "user_id": quota.user_id,
            "resource_type": quota.resource_type,
            "limit_value": quota.limit_value,
            "period": quota.period,
        },
    }


@router.get("/quotas")
async def list_quotas(tenant_id: Optional[str] = Query(None), authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    quotas = usage_quota_manager.list_quotas(tenant_id=tenant_id)
    return {"status": "OK", "quotas": quotas}


@router.get("/quotas/check")
async def check_quota(tenant_id: str, user_id: str, resource_type: str, quantity: float = Query(1.0), authorization: str = Header(None)):
    user_id_auth = get_user_id_from_token(authorization)
    result = usage_quota_manager.check_quota(tenant_id, user_id, resource_type, quantity)
    return {"status": "OK", **result}
