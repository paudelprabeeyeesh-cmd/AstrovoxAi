from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ToolHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ToolDefinitionModel(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    required_permissions: List[str] = []
    timeout_seconds: float = 30.0
    tags: List[str] = []
    version: str = "1.0.0"
    deprecated: bool = False
    health: ToolHealthStatus = ToolHealthStatus.UNKNOWN
    owner: Optional[str] = None


class ToolRegistrationRequest(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    required_permissions: List[str] = []
    timeout_seconds: float = 30.0
    tags: List[str] = []
    version: str = "1.0.0"
    deprecated: bool = False
    owner: Optional[str] = None


class ToolExecuteRequestModel(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    user_id: Optional[str] = None


class ToolExecuteResponseModel(BaseModel):
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    approval_id: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None


class ToolApproveRequestModel(BaseModel):
    approval_id: str
    approver_user_id: Optional[str] = None


class ToolApproveResponseModel(BaseModel):
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ToolMetricsResponse(BaseModel):
    tool_name: str
    total_calls: int
    success_count: int
    failure_count: int
    avg_duration_ms: float
    error_rate: float
    health_status: ToolHealthStatus
    pending_approvals: int
    circuit_breaker_rejections: int
    last_call_at: Optional[float] = None


class ApprovalSummary(BaseModel):
    approval_id: str
    tool_name: str
    arguments: Dict[str, Any]
    user_id: str
    tier: str
    operation: str
    status: str
    created_at: float
    ttl_seconds: float
    remaining_ttl: Optional[float] = None
