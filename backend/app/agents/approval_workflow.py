from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ApprovalWorkflow:
    def __init__(self, approvers: Optional[List[str]] = None):
        self.approvers = approvers or []
        self.requests: Dict[str, Dict[str, Any]] = {}

    def request_approval(self, request_id: str, payload: Dict[str, Any], required_approvers: int = 1) -> Dict[str, Any]:
        if request_id in self.requests:
            raise ValueError(f"Duplicate approval request: {request_id}")
        record = {
            "request_id": request_id,
            "payload": payload,
            "status": "pending",
            "approvals": [],
            "required_approvers": required_approvers,
        }
        self.requests[request_id] = record
        logger.info("Approval requested: %s", request_id)
        return record

    def approve(self, request_id: str, approver: str) -> Dict[str, Any]:
        record = self.requests.get(request_id)
        if not record:
            raise ValueError(f"Unknown approval request: {request_id}")
        if record["status"] != "pending":
            return record
        record["approvals"].append(approver)
        if len(record["approvals"]) >= record["required_approvers"]:
            record["status"] = "approved"
            logger.info("Approval granted: %s by %s", request_id, approver)
        return record

    def reject(self, request_id: str, approver: str, reason: str = "") -> Dict[str, Any]:
        record = self.requests.get(request_id)
        if not record:
            raise ValueError(f"Unknown approval request: {request_id}")
        record["status"] = "rejected"
        record["rejection_reason"] = reason
        record["rejected_by"] = approver
        logger.info("Approval rejected: %s by %s", request_id, approver)
        return record

    def get_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        return self.requests.get(request_id)
