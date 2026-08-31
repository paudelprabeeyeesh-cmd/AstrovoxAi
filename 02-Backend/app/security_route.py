"""Security audit API routes."""

from fastapi import APIRouter, Header

from .security_audit import security_auditor
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/audit")
async def run_security_audit(authorization: str = Header(None)):
    """Run a full security audit."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", **security_auditor.run_full_audit()}


@router.get("/check/environment")
async def check_environment(authorization: str = Header(None)):
    """Check environment security."""
    user_id = get_user_id_from_token(authorization)
    findings = security_auditor.audit_environment()
    return {
        "status": "OK",
        "findings": [
            {"title": f.title, "severity": f.severity.value, "recommendation": f.recommendation}
            for f in findings
        ],
    }
