from dataclasses import dataclass
from typing import List

from sandboxing.code_executor import CodeExecutor, ExecutionResult
from sandboxing.permission_checker import PermissionChecker, PermissionProfile
from sandboxing.resource_limiter import ResourceLimiter


@dataclass
class SandboxResult:
    success: bool
    output: str
    error: str
    permission_denied: bool


class Sandbox:
    def __init__(self, profile: PermissionProfile, limiter: ResourceLimiter):
        self.profile = profile
        self.checker = PermissionChecker(profile)
        self.executor = CodeExecutor(timeout=profile.max_execution_time)
        self.limiter = limiter

    def execute(self, code: str) -> SandboxResult:
        blocked = self.checker.check_imports(code)
        if blocked:
            return SandboxResult(
                success=False,
                output="",
                error=f"blocked imports: {blocked}",
                permission_denied=True,
            )
        if not self.checker.apply(code):
            return SandboxResult(
                success=False,
                output="",
                error="permission check failed",
                permission_denied=True,
            )
        try:
            self.limiter.enforce_with_timeout()
        except (OSError, ValueError):
            pass
        result = self.executor.run(code)
        return SandboxResult(
            success=result.success,
            output=result.output,
            error=result.error,
            permission_denied=False,
        )
