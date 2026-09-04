"""
FastAPI router exposing the secure code execution service.

Replaces the legacy `/tools/execute` endpoint that allowed in-process
`exec()`. This router is registered under `/sandbox` and requires
admin authentication.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth_utils import get_current_user
from .security_hardening import Principal, principal_from_jwt_claims
from .secure_executor import (
    SandboxConfig,
    execute_user_code,
)
from .iam import require_admin


router = APIRouter(prefix="/sandbox", tags=["sandbox"])


class ExecuteRequest(BaseModel):
    code: str = Field(..., max_length=50_000)
    timeout_s: float = Field(default=5.0, ge=0.1, le=30.0)
    memory_mb: int = Field(default=256, ge=64, le=2048)
    use_docker: bool = False


class ExecuteResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    duration_ms: float
    exit_code: int
    timed_out: bool
    truncated: bool


@router.post("/execute", response_model=ExecuteResponse)
async def execute_code(
    req: ExecuteRequest,
    principal: Principal = Depends(require_admin),
) -> ExecuteResponse:
    """Execute untrusted Python code in a sandboxed environment.

    Requires admin role. Code runs with strict CPU/memory/time limits,
    no network access, and a read-only filesystem.
    """
    config = SandboxConfig(
        timeout_s=req.timeout_s,
        memory_mb=req.memory_mb,
    )
    result = execute_user_code(
        req.code,
        use_docker=req.use_docker,
        config=config,
        principal=principal,
    )
    return ExecuteResponse(
        success=result.success,
        output=result.output,
        error=result.error,
        duration_ms=result.duration_ms,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        truncated=result.truncated,
    )


@router.get("/health")
async def sandbox_health() -> Dict[str, Any]:
    import os
    import shutil

    return {
        "status": "ok",
        "docker_available": shutil.which("docker") is not None,
        "use_docker_default": os.getenv("ASTROVOX_USE_DOCKER_SANDBOX", "false") == "true",
    }
