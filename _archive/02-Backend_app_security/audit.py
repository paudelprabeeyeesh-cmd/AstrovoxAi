"""Enhanced security audit logging system.

Integrates with:
1. Sandboxing violations
2. Secret scanning results
3. Security policy violations
4. Compliance reporting
"""

from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    SANDBOX_VIOLATION = "sandbox_violation"
    SECRET_DETECTED = "secret_detected"
    POLICY_VIOLATION = "policy_violation"
    SECURITY_SCAN = "security_scan"
    COMPLIANCE_CHECK = "compliance_check"
    ADMIN_ACTION = "admin_action"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """A security audit event."""
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: float = field(default_factory=time.time)
    user_id: str = "system"
    session_id: Optional[str] = None
    ip_address: str = "0.0.0.0"
    resource: str = ""
    action: str = ""
    outcome: str = "success"  # success, failure, blocked
    details: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "resource": self.resource,
            "action": self.action,
            "outcome": self.outcome,
            "details": self.details,
            "tags": self.tags
        }


class EnhancedAuditLogger:
    """Enhanced audit logger with integration capabilities."""

    def __init__(self, max_memory_events: int = 10000):
        self._events: List[AuditEvent] = []
        self._max_memory_events = max_memory_events
        self._lock = threading.RLock()
        self._handlers: List[callable] = []

    def add_handler(self, handler: callable):
        """Add an event handler (called for each audit event)."""
        self._handlers.append(handler)

    def _emit_event(self, event: AuditEvent):
        """Emit an event to all handlers."""
        with self._lock:
            # Add to memory buffer
            self._events.append(event)
            
            # Trim if too large
            if len(self._events) > self._max_memory_events:
                self._events = self._events[-self._max_memory_events:]
            
            # Log to standard logger
            log_level = {
                AuditSeverity.INFO: logging.INFO,
                AuditSeverity.WARNING: logging.WARNING,
                AuditSeverity.ERROR: logging.ERROR,
                AuditSeverity.CRITICAL: logging.CRITICAL
            }[event.severity]
            
            logger.log(
                log_level,
                f"AUDIT: {event.event_type.value} - {event.action} "
                f"user={event.user_id} ip={event.ip_address} "
                f"outcome={event.outcome}"
            )
            
            # Call custom handlers
            for handler in self._handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Audit handler failed: {e}")

    def log_authentication(
        self,
        user_id: str,
        ip_address: str,
        success: bool,
        method: str = "password",
        details: Dict[str, Any] = None
    ):
        """Log an authentication event."""
        event = AuditEvent(
            event_type=AuditEventType.AUTHENTICATION,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            resource="authentication_system",
            action="login",
            outcome="success" if success else "failure",
            details=details or {"method": method, "success": success}
        )
        self._emit_event(event)

    def log_authorization(
        self,
        user_id: str,
        ip_address: str,
        resource: str,
        action: str,
        granted: bool,
        details: Dict[str, Any] = None
    ):
        """Log an authorization check."""
        event = AuditEvent(
            event_type=AuditEventType.AUTHORIZATION,
            severity=AuditSeverity.INFO if granted else AuditSeverity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            outcome="granted" if granted else "denied",
            details=details or {"granted": granted}
        )
        self._emit_event(event)

    def log_data_access(
        self,
        user_id: str,
        ip_address: str,
        resource: str,
        action: str,
        details: Dict[str, Any] = None
    ):
        """Log a data access event."""
        event = AuditEvent(
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            outcome="success",
            details=details or {}
        )
        self._emit_event(event)

    def log_sandbox_violation(
        self,
        user_id: str,
        ip_address: str,
        violation_type: str,
        details: Dict[str, Any] = None
    ):
        """Log a sandbox violation."""
        event = AuditEvent(
            event_type=AuditEventType.SANDBOX_VIOLATION,
            severity=AuditSeverity.ERROR,
            user_id=user_id,
            ip_address=ip_address,
            resource="sandbox",
            action="violation_detected",
            outcome="blocked",
            details=details or {"violation_type": violation_type}
        )
        self._emit_event(event)

    def log_secret_detected(
        self,
        user_id: str,
        ip_address: str,
        secret_type: str,
        file_path: str,
        details: Dict[str, Any] = None
    ):
        """Log a detected secret."""
        event = AuditEvent(
            event_type=AuditEventType.SECRET_DETECTED,
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            ip_address=ip_address,
            resource=file_path,
            action="secret_detected",
            outcome="blocked",
            details=details or {
                "secret_type": secret_type,
                "file_path": file_path
            }
        )
        self._emit_event(event)

    def log_policy_violation(
        self,
        user_id: str,
        ip_address: str,
        policy_name: str,
        violation_details: str,
        details: Dict[str, Any] = None
    ):
        """Log a policy violation."""
        event = AuditEvent(
            event_type=AuditEventType.POLICY_VIOLATION,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            resource=policy_name,
            action="policy_violation",
            outcome="blocked",
            details=details or {"policy": policy_name, "violation": violation_details}
        )
        self._emit_event(event)

    def log_security_scan(
        self,
        user_id: str,
        ip_address: str,
        scan_type: str,
        results: Dict[str, Any],
        details: Dict[str, Any] = None
    ):
        """Log a security scan result."""
        event = AuditEvent(
            event_type=AuditEventType.SECURITY_SCAN,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            ip_address=ip_address,
            resource="security_scanner",
            action="scan_completed",
            outcome="success",
            details=details or {
                "scan_type": scan_type,
                "results_summary": results
            }
        )
        self._emit_event(event)

    def log_admin_action(
        self,
        user_id: str,
        ip_address: str,
        action: str,
        target: str,
        details: Dict[str, Any] = None
    ):
        """Log an administrative action."""
        event = AuditEvent(
            event_type=AuditEventType.ADMIN_ACTION,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            ip_address=ip_address,
            resource=target,
            action=action,
            outcome="success",
            details=details or {}
        )
        self._emit_event(event)

    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        since: float = 0,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get audit events with filtering."""
        with self._lock:
            events = [e for e in self._events if e.timestamp >= since]
            
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            if user_id:
                events = [e for e in events if e.user_id == user_id]
            
            # Sort by timestamp descending (newest first)
            events.sort(key=lambda e: e.timestamp, reverse=True)
            
            return events[:limit]

    def get_event_counts(self, since: float = 0) -> Dict[str, Any]:
        """Get counts of events by type and severity."""
        with self._lock:
            events = [e for e in self._events if e.timestamp >= since]
            
            by_type: Dict[str, int] = {}
            by_severity: Dict[str, int] = {}
            by_outcome: Dict[str, int] = {}
            
            for event in events:
                event_type = event.event_type.value
                severity = event.severity.value
                outcome = event.outcome
                
                by_type[event_type] = by_type.get(event_type, 0) + 1
                by_severity[severity] = by_severity.get(severity, 0) + 1
                by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
            
            return {
                "total_events": len(events),
                "by_type": by_type,
                "by_severity": by_severity,
                "by_outcome": by_outcome,
                "time_window_seconds": time.time() - since if since > 0 else None
            }

    def export_events(self, format: str = "json", since: float = 0) -> str:
        """Export audit events."""
        with self._lock:
            events = [e for e in self._events if e.timestamp >= since]
            events_data = [e.to_dict() for e in events]
            
            if format == "json":
                return json.dumps(events_data, indent=2, default=str)
            elif format == "csv":
                # Simple CSV export
                if not events_data:
                    return ""
                
                headers = list(events_data[0].keys())
                lines = [",".join(headers)]
                for row in events_data:
                    values = [str(row.get(h, "")) for h in headers]
                    lines.append(",".join(values))
                return "\n".join(lines)
            else:
                raise ValueError(f"Unsupported format: {format}")


# Global enhanced audit logger
enhanced_audit_logger = EnhancedAuditLogger()

# Convenience functions
def log_authentication(user_id: str, ip_address: str, success: bool, **kwargs):
    """Log authentication event."""
    enhanced_audit_logger.log_authentication(user_id, ip_address, success, **kwargs)

def log_authorization(user_id: str, ip_address: str, resource: str, action: str, granted: bool, **kwargs):
    """Log authorization event."""
    enhanced_audit_logger.log_authorization(user_id, ip_address, resource, action, granted, **kwargs)

def log_data_access(user_id: str, ip_address: str, resource: str, action: str, **kwargs):
    """Log data access event."""
    enhanced_audit_logger.log_data_access(user_id, ip_address, resource, action, **kwargs)

def log_sandbox_violation(user_id: str, ip_address: str, violation_type: str, **kwargs):
    """Log sandbox violation."""
    enhanced_audit_logger.log_sandbox_violation(user_id, ip_address, violation_type, **kwargs)

def log_secret_detected(user_id: str, ip_address: str, secret_type: str, file_path: str, **kwargs):
    """Log secret detection."""
    enhanced_audit_logger.log_secret_detected(user_id, ip_address, secret_type, file_path, **kwargs)

def log_policy_violation(user_id: str, ip_address: str, policy_name: str, violation_details: str, **kwargs):
    """Log policy violation."""
    enhanced_audit_logger.log_policy_violation(user_id, ip_address, policy_name, violation_details, **kwargs)

def log_security_scan(user_id: str, ip_address: str, scan_type: str, results: Dict[str, Any], **kwargs):
    """Log security scan."""
    enhanced_audit_logger.log_security_scan(user_id, ip_address, scan_type, results, **kwargs)

def log_admin_action(user_id: str, ip_address: str, action: str, target: str, **kwargs):
    """Log admin action."""
    enhanced_audit_logger.log_admin_action(user_id, ip_address, action, target, **kwargs)

def get_audit_events(**kwargs) -> List[AuditEvent]:
    """Get audit events."""
    return enhanced_audit_logger.get_events(**kwargs)

def export_audit_log(format: str = "json", since: float = 0) -> str:
    """Export audit log."""
    return enhanced_audit_logger.export_events(format, since)


# Integration with existing audit logger
def _integrate_with_existing_audit_logger():
    """Integrate with the existing audit logger from security.py."""
    try:
        from app.security import audit_logger
        
        # Add a handler to forward events to the existing logger
        def forward_to_existing(event: AuditEvent):
            # Map to existing AuditEvent format
            existing_event = audit_logger.AuditEvent(
                event_type=f"{event.event_type.value}_{event.action}",
                user_id=event.user_id,
                ip_address=event.ip_address,
                timestamp=event.timestamp,
                details=event.details,
                severity=event.severity.value
            )
            audit_logger._events.append(existing_event)
            
            # Keep the existing logger's size in check
            if len(audit_logger._events) > 1000:
                audit_logger._events = audit_logger._events[-1000:]
        
        enhanced_audit_logger.add_handler(forward_to_existing)
        logger.info("Integrated enhanced audit logger with existing audit logger")
        
    except ImportError:
        logger.warning("Could not integrate with existing audit logger")


# Auto-integrate on import
_integrate_with_existing_audit_logger()


# Export for easy access
__all__ = [
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
    "export_audit_log"
]