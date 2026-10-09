
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/security", tags=["security"])


class SecurityCertificationCreate(BaseModel):
    certification_name: str
    certification_body: str
    issued_at: str
    expires_at: Optional[str] = None
    certificate_url: Optional[str] = None
    scope: Optional[str] = None


@router.post("/organizations/{org_id}/certifications")
def create_certification(org_id: str, payload: SecurityCertificationCreate, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    from ..security_certifications import create_security_certification
    return create_security_certification(org_id, payload.certification_name, payload.certification_body, payload.issued_at, payload.expires_at, payload.certificate_url, payload.scope)


@router.get("/organizations/{org_id}/certifications")
def list_certifications(org_id: str, status: Optional[str] = None):
    from ..security_certifications import list_security_certifications
    return list_security_certifications(org_id, status)


@router.get("/organizations/{org_id}/certifications/{cert_id}")
def get_certification(org_id: str, cert_id: str):
    from ..security_certifications import get_security_certification
    cert = get_security_certification(cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    return cert


@router.put("/organizations/{org_id}/certifications/{cert_id}")
def update_certification(org_id: str, cert_id: str, payload: SecurityCertificationCreate):
    from ..security_certifications import update_security_certification
    return update_security_certification(cert_id, **payload.model_dump(exclude_none=True))


@router.delete("/organizations/{org_id}/certifications/{cert_id}")
def delete_certification(org_id: str, cert_id: str, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    from ..security_certifications import delete_security_certification
    success = delete_security_certification(cert_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Certification not found")
    return {"ok": True}


@router.get("/organizations/{org_id}/certifications/expiring")
def expiring_certifications(org_id: str, days_ahead: int = Query(30, ge=1, le=365)):
    from ..security_certifications import check_expiring_certifications
    return check_expiring_certifications(org_id, days_ahead)
