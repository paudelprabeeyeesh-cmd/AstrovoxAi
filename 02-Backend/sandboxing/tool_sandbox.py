import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

from sandboxing.approval_store import approval_store
from sandboxing.permission_tiers import PermissionDecision, PermissionEngine, PermissionTier
from sandboxing.command_scrubbing import CommandScrubber
from sandboxing.tool_metrics import tool_metrics
from app.circuit_breaker import CircuitBreaker, CircuitState
from app.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class ToolSandboxStatus(str, Enum):
    APPROVED = "approved"
    PENDING_APPROVAL = "pending_approval"
    DENIED = "denied"
    BLOCKED = "blocked"
    ERROR = "error"


class ToolPermissionTier(str, Enum):
    READ = "read"
    WRITE = "write"
    DANGEROUS = "dangerous"


TOOL_TIER_MAP: Dict[str, ToolPermissionTier] = {
    "search_web": ToolPermissionTier.READ,
    "calculate": ToolPermissionTier.READ,
    "get_current_time": ToolPermissionTier.READ,
    "get_weather": ToolPermissionTier.READ,
    "search_documents": ToolPermissionTier.READ,
    "memory_search": ToolPermissionTier.READ,
    "file_read": ToolPermissionTier.READ,
    "pdf_read": ToolPermissionTier.READ,
    "create_memory": ToolPermissionTier.WRITE,
    "file_write": ToolPermissionTier.WRITE,
    "send_email": ToolPermissionTier.WRITE,
    "image_generate": ToolPermissionTier.WRITE,
    "voice_speak": ToolPermissionTier.WRITE,
    "deep_research": ToolPermissionTier.WRITE,
    "web_fetch": ToolPermissionTier.WRITE,
    "code_execute": ToolPermissionTier.WRITE,
    "bash": ToolPermissionTier.DANGEROUS,
    "text_editor": ToolPermissionTier.DANGEROUS,
    "computer_use": ToolPermissionTier.DANGEROUS,
}


@dataclass
class ToolSandboxResult:
    status: ToolSandboxStatus
    output: Optional[str] = None
    error: Optional[str] = None
    approval_id: Optional[str] = None
    message: Optional[str] = None
    details: Optional[dict] = None


class ToolSandbox:
    def __init__(
        self,
        permission_engine: Optional[PermissionEngine] = None,
        tool_executor: Optional[Any] = None,
        tool_circuit_breaker: Optional[CircuitBreaker] = None,
        max_retries: int = 2,
        approval_ttl_seconds: float = 300.0,
    ) -> None:
        self.permission_engine = permission_engine or PermissionEngine()
        self.tool_executor = tool_executor
        self.circuit_breaker = tool_circuit_breaker or CircuitBreaker(
            name="tool_executor",
            failure_threshold=5,
            recovery_timeout=30,
            success_threshold=3,
        )
        self.max_retries = max_retries
        self.approval_ttl_seconds = approval_ttl_seconds
        self._per_tool_breakers: Dict[str, CircuitBreaker] = {}

    def _get_tier(self, tool_name: str) -> ToolPermissionTier:
        return TOOL_TIER_MAP.get(tool_name, ToolPermissionTier.WRITE)

    def _get_operation(self, tool_name: str, arguments: dict) -> str:
        parts = [tool_name]
        for key in ["command", "code", "file_path", "url", "operation"]:
            if key in arguments:
                parts.append(f"{key}={arguments[key]}")
                break
        return " ".join(parts)

    def _get_per_tool_breaker(self, tool_name: str) -> CircuitBreaker:
        if tool_name not in self._per_tool_breakers:
            self._per_tool_breakers[tool_name] = CircuitBreaker(
                name=f"tool:{tool_name}",
                failure_threshold=5,
                recovery_timeout=30,
                success_threshold=3,
            )
        return self._per_tool_breakers[tool_name]

    def _has_permission(self, user_id: str, tool_name: str) -> bool:
        from app.rbac import has_permission, Permission
        dangerous_tools = {"bash", "text_editor", "computer_use", "code_execute", "file_write"}
        required = Permission.ADMIN if tool_name in dangerous_tools else Permission.WRITE
        return has_permission(user_id, required.value, f"tool:{tool_name}")

    def check_permission(self, tool_name: str, user_id: str, arguments: dict) -> ToolSandboxResult:
        if not self._has_permission(user_id, tool_name):
            self._log_safety_block(user_id, tool_name, arguments, "rbac_denied")
            return ToolSandboxResult(
                status=ToolSandboxStatus.DENIED,
                error=f"Permission denied for tool '{tool_name}'",
            )

        tier = self._get_tier(tool_name)
        operation = self._get_operation(tool_name, arguments)
        decision: PermissionDecision = self.permission_engine.evaluate(operation, PermissionTier(tier.value))

        if not decision.approved:
            if decision.reversible:
                approval = approval_store.create(
                    tool_name=tool_name,
                    arguments=arguments,
                    user_id=user_id,
                    tier=tier.value,
                    operation=operation,
                    ttl_seconds=self.approval_ttl_seconds,
                )
                tool_metrics.record_approval_pending(tool_name)
                self._log_event(
                    "tool_approval_required",
                    user_id,
                    f"tool:{tool_name}",
                    tool_name,
                    {
                        "approval_id": approval.approval_id,
                        "tier": tier.value,
                        "operation": operation,
                        "arguments": arguments,
                    },
                    "pending",
                )
                return ToolSandboxResult(
                    status=ToolSandboxStatus.PENDING_APPROVAL,
                    approval_id=approval.approval_id,
                    message=decision.message,
                )
            self._log_safety_block(user_id, tool_name, arguments, "dangerous_denied", operation=operation)
            return ToolSandboxResult(
                status=ToolSandboxStatus.BLOCKED,
                error=decision.message,
            )

        return ToolSandboxResult(status=ToolSandboxStatus.APPROVED)

    def _execute_with_resilience(self, tool_name: str, arguments: dict, user_id: str) -> ToolSandboxResult:
        per_tool_breaker = self._get_per_tool_breaker(tool_name)

        @retry_with_backoff(max_retries=self.max_retries, base_delay=1.0, max_delay=10.0, jitter=True)
        def _run() -> str:
            if per_tool_breaker.state == CircuitState.OPEN:
                tool_metrics.record_circuit_breaker_rejection(tool_name)
                raise Exception(f"Circuit breaker open for tool '{tool_name}'")
            if self.circuit_breaker.state == CircuitState.OPEN:
                tool_metrics.record_circuit_breaker_rejection(tool_name)
                raise Exception(f"Global circuit breaker open for tool '{tool_name}'")
            if not self.tool_executor:
                raise RuntimeError("Tool executor not configured")
            return self.tool_executor.execute_tool(tool_name, arguments, user_id)

        try:
            output = per_tool_breaker.call(_run)
            return ToolSandboxResult(status=ToolSandboxStatus.APPROVED, output=output)
        except Exception as exc:
            logger.error("Tool execution failed for %s: %s", tool_name, exc)
            return ToolSandboxResult(status=ToolSandboxStatus.ERROR, error=str(exc))

    def execute(self, tool_name: str, arguments: dict, user_id: str) -> ToolSandboxResult:
        scrubber = CommandScrubber()
        command_value = arguments.get("command") or arguments.get("code") or ""
        if command_value:
            scrub_result = scrubber.scan(str(command_value))
            if scrub_result.blocked:
                self._log_safety_block(user_id, tool_name, arguments, "command_scrubber", matched_rules=scrub_result.matched_rules)
                return ToolSandboxResult(
                    status=ToolSandboxStatus.BLOCKED,
                    error=f"Command blocked by scrubber: {scrub_result.matched_rules}",
                )

        permission_result = self.check_permission(tool_name, user_id, arguments)
        if permission_result.status != ToolSandboxStatus.APPROVED:
            return permission_result

        execution_result = self._execute_with_resilience(tool_name, arguments, user_id)
        self._log_tool_call(user_id, tool_name, arguments, execution_result)
        return execution_result

    def approve(self, approval_id: str, approver_user_id: str) -> Optional[ToolSandboxResult]:
        approval = approval_store.approve(approval_id, resolved_by=approver_user_id)
        if not approval:
            return ToolSandboxResult(status=ToolSandboxStatus.DENIED, error="Approval not found or expired")
        if approval.user_id != approver_user_id:
            self._log_event(
                "tool_approval_mismatch",
                approver_user_id,
                f"approve:{approval_id}",
                approval.tool_name,
                {"expected_user": approval.user_id, "actual_user": approver_user_id},
                "denied",
            )
            return ToolSandboxResult(status=ToolSandboxStatus.DENIED, error="Approver does not match requester")

        tool_metrics.record_approval_completed(approval.tool_name)
        self._log_event(
            "tool_approval_granted",
            approver_user_id,
            f"approve:{approval_id}",
            approval.tool_name,
            {"approval_id": approval_id, "tier": approval.tier, "operation": approval.operation},
            "approved",
        )
        return self._execute_approved(approval.tool_name, approval.arguments, approval.user_id)

    def reject(self, approval_id: str, approver_user_id: str) -> Optional[ToolSandboxResult]:
        approval = approval_store.reject(approval_id, resolved_by=approver_user_id)
        if not approval:
            return ToolSandboxResult(status=ToolSandboxStatus.DENIED, error="Approval not found or expired")
        tool_metrics.record_approval_completed(approval.tool_name)
        self._log_event(
            "tool_approval_rejected",
            approver_user_id,
            f"reject:{approval_id}",
            approval.tool_name,
            {"approval_id": approval_id},
            "rejected",
        )
        return ToolSandboxResult(status=ToolSandboxStatus.DENIED, error="Approval rejected by user")

    def _execute_approved(self, tool_name: str, arguments: dict, user_id: str) -> ToolSandboxResult:
        scrubber = CommandScrubber()
        command_value = arguments.get("command") or arguments.get("code") or ""
        if command_value:
            scrub_result = scrubber.scan(str(command_value))
            if scrub_result.blocked:
                self._log_safety_block(user_id, tool_name, arguments, "command_scrubber", matched_rules=scrub_result.matched_rules)
                return ToolSandboxResult(
                    status=ToolSandboxStatus.BLOCKED,
                    error=f"Command blocked by scrubber: {scrub_result.matched_rules}",
                )

        execution_result = self._execute_with_resilience(tool_name, arguments, user_id)
        self._log_tool_call(user_id, tool_name, arguments, execution_result)
        return execution_result

    def _log_safety_block(self, actor: str, tool_name: str, arguments: dict, reason: str, **extra):
        from app.audit import audit_logger
        audit_logger.log_safety_block(
            actor=actor,
            action=f"tool:{tool_name}",
            target=tool_name,
            details={"reason": reason, "arguments": arguments, **extra},
        )

    def _log_event(self, event_type: str, actor: str, action: str, target: str, details: dict, status: str):
        from app.audit import audit_logger
        audit_logger.log(event_type=event_type, actor=actor, action=action, target=target, details=details, status=status)

    def _log_tool_call(self, actor: str, tool_name: str, arguments: dict, execution_result: ToolSandboxResult):
        from app.audit import audit_logger
        audit_logger.log_tool_call(
            actor=actor,
            action=f"tool:{tool_name}",
            target=tool_name,
            details={
                "status": execution_result.status.value,
                "arguments": arguments,
                "output_preview": (execution_result.output or "")[:500] if execution_result.output else None,
            },
        )
