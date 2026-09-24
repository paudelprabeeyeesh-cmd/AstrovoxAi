
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/compliance", tags=["compliance"])


class RetentionPolicyCreate(BaseModel):
    policy_name: str
    data_type: str
    retention_days: int
    auto_delete: bool = False
    archive_before_delete: bool = False


class DeletionRequestCreate(BaseModel):
    request_type: str
    reason: Optional[str] = None


class ComplianceReportCreate(BaseModel):
    report_type: str
    framework: str
    period_start: str
    period_end: str


@router.post("/organizations/{org_id}/retention-policies")
def create_retention_policy(org_id: str, payload: RetentionPolicyCreate, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    from ..data_retention import create_data_retention_policy
    return create_data_retention_policy(org_id, payload.policy_name, payload.data_type, payload.retention_days, payload.auto_delete, payload.archive_before_delete)


@router.get("/organizations/{org_id}/retention-policies")
def list_retention_policies(org_id: str):
    from ..data_retention import list_data_retention_policies
    return list_data_retention_policies(org_id)


@router.post("/organizations/{org_id}/retention-policies/{policy_id}/apply")
def apply_retention_policies(org_id: str, policy_id: str):
    from ..data_retention import apply_retention_policies
    return apply_retention_policies(org_id)


@router.post("/organizations/{org_id}/deletion-requests")
def create_deletion_request(org_id: str, payload: DeletionRequestCreate, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    from ..data_retention import create_deletion_request
    return create_deletion_request(org_id, user_id, payload.request_type, payload.reason)


@router.get("/organizations/{org_id}/deletion-requests")
def list_deletion_requests(org_id: str, status: Optional[str] = None):
    from ..data_retention import list_deletion_requests
    return list_deletion_requests(org_id, status)


@router.post("/deletion-requests/{request_id}/process")
def process_deletion_request(request_id: str, approved: bool = Query(...), authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    from ..data_retention import process_deletion_request
    return process_deletion_request(request_id, user_id, approved)


@router.post("/organizations/{org_id}/reports")
def create_compliance_report(org_id: str, payload: ComplianceReportCreate, authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    user_id = info["user_id"]
    from ..compliance_dashboard import create_compliance_report
    return create_compliance_report(org_id, payload.report_type, payload.framework, payload.period_start, payload.period_end, user_id)


@router.get("/organizations/{org_id}/reports")
def list_compliance_reports(org_id: str, framework: Optional[str] = None, report_type: Optional[str] = None):
    from ..compliance_dashboard import list_compliance_reports
    return list_compliance_reports(org_id, framework, report_type)


@router.get("/organizations/{org_id}/reports/{report_id}")
def get_compliance_report(org_id: str, report_id: str):
    from ..compliance_dashboard import get_compliance_report
    report = get_compliance_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/organizations/{org_id}/dashboard")
def compliance_dashboard(org_id: str):
    from ..compliance_dashboard import get_compliance_dashboard
    return get_compliance_dashboard(org_id)


@router.post("/organizations/{org_id}/gdpr/export")
def gdpr_data_export(org_id: str, user_id: str = Query(...)):
    from ..compliance import export_user_data
    data = export_user_data(user_id)
    return data


@router.delete("/organizations/{org_id}/gdpr/delete")
def gdpr_data_delete(org_id: str, user_id: str = Query(...), authorization: Optional[str] = None):
    from ..auth import get_user_id_from_token_with_roles
    info = get_user_id_from_token_with_roles(authorization)
    requester_id = info["user_id"]
    from ..compliance import delete_user_data
    result = delete_user_data(user_id)
    log_action(requester_id, "gdpr_delete_user_data", f"user:{user_id}", {"org_id": org_id})
    return result
