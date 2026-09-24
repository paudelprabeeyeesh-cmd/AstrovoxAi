
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/custom-domains", tags=["custom-domains"])


class DomainCreate(BaseModel):
    domain: str


@router.post("/")
def create_domain(org_id: str = Query(...), payload: DomainCreate = ..., authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    from ..custom_domains import create_custom_domain
    return create_custom_domain(org_id, payload.domain)


@router.get("/")
def list_domains(org_id: str = Query(...)):
    from ..custom_domains import list_custom_domains
    return list_custom_domains(org_id)


@router.get("/{domain_id}")
def get_domain(domain_id: str):
    from ..custom_domains import get_custom_domain
    domain = get_custom_domain(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.post("/{domain_id}/verify")
def verify_domain(domain_id: str):
    from ..custom_domains import verify_domain
    return verify_domain(domain_id)


@router.put("/{domain_id}/ssl")
def update_ssl(domain_id: str, ssl_status: str = Query(...), cert_path: Optional[str] = None, key_path: Optional[str] = None):
    from ..custom_domains import update_ssl_status
    return update_ssl_status(domain_id, ssl_status, cert_path, key_path)


@router.delete("/{domain_id}")
def delete_domain(domain_id: str, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    from ..custom_domains import delete_custom_domain
    success = delete_custom_domain(domain_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Domain not found")
    return {"ok": True}
