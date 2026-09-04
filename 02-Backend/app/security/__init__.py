"""Security package for AstrovoxAi.

Provides:
1. Sandboxing for safe code execution
2. Secret scanning for detecting sensitive data
3. Enhanced audit logging
4. Integration with existing security systems
"""

from __future__ import annotations

# Import key components for easy access
from .sandbox import (
    SandboxExecutor,
    SandboxResult,
    SandboxLimits,
    SandboxProfile,
    SANDBOX_PROFILES,
    SandboxViolation,
    execute_python_sandboxed,
    execute_command_sandboxed
)

from .secret_scanner import (
    SecretScanner,
    SecretFinding,
    SecretType,
    secret_scanner,
    scan_string,
    scan_file,
    scan_directory,
    scan_content
)

from .audit import (
    AuditEventType,
    AuditSeverity,
    AuditEvent,
    EnhancedAuditLogger,
    enhanced_audit_logger,
    log_authentication,
    log_authorization,
    log_data_access,
    log_sandbox_violation,
    log_secret_detected,
    log_policy_violation,
    log_security_scan,
    log_admin_action,
    get_audit_events,
    export_audit_log
)

# Version information
__version__ = "1.0.0"
__author__ = "AstrovoxAi Security Team"

# Package-level convenience functions
def scan_for_secrets_in_content(content: str, filename: str = "<content>") -> dict:
    """Convenience function to scan content for secrets."""
    return scan_content(content, filename)

def execute_in_sandbox(
    code: str,
    language: str = "python",
    profile: str = "moderate",
    **kwargs
):
    """Convenience function to execute code in a sandbox."""
    if language.lower() == "python":
        return execute_python_sandboxed(code, profile=profile, **kwargs)
    else:
        raise ValueError(f"Unsupported language for sandboxing: {language}")

# Export all public interfaces
__all__ = [
    # Sandboxing
    "SandboxExecutor",
    "SandboxResult",
    "SandboxLimits",
    "SandboxProfile",
    "SANDBOX_PROFILES",
    "SandboxViolation",
    "execute_python_sandboxed",
    "execute_command_sandboxed",
    
    # Secret Scanning
    "SecretScanner",
    "SecretFinding",
    "SecretType",
    "secret_scanner",
    "scan_string",
    "scan_file",
    "scan_directory",
    "scan_content",
    
    # Audit Logging
    "AuditEventType",
    "AuditSeverity",
    "AuditEvent",
    "EnhancedAuditLogger",
    "enhanced_audit_logger",
    "log_authentication",
    "log_authorization",
    "log_data_access",
    "log_sandbox_violation",
    "log_secret_detected",
    "log_policy_violation",
    "log_security_scan",
    "log_admin_action",
    "get_audit_events",
    "export_audit_log",
    
    # Convenience functions
    "scan_for_secrets_in_content",
    "execute_in_sandbox",
    
    # Metadata
    "__version__",
    "__author__"
]