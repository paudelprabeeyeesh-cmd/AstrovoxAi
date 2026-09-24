from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ToolSandboxStatus(str, Enum):
    APPROVED = "approved"
    PENDING_APPROVAL = "pending_approval"
    DENIED = "denied"
    BLOCKED = "blocked"
    ERROR = "error"


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]


class ToolExecuteResponse(BaseModel):
    status: ToolSandboxStatus
    output: Optional[str] = None
    error: Optional[str] = None
    approval_id: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ToolApproveRequest(BaseModel):
    approval_id: str


class ToolApproveResponse(BaseModel):
    status: ToolSandboxStatus
    output: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
