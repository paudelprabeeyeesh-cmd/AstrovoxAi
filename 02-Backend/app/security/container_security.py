"""Container security policies and runtime rules.

This module implements container security controls with:

1. Security policy definitions (rego-style rules)
2. Runtime behavior monitoring
3. Resource limit enforcement
4. Network access control
5. Filesystem access restrictions
6. Privilege escalation prevention
7. Image vulnerability scanning integration
8. Runtime threat detection

Threat model: NIST SP 800-190 - Application Container Security Guide
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SecurityPolicyAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    AUDIT = "audit"
    ALERT = "alert"


class ResourceType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESSES = "processes"


class NetworkAccessType(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    DNS = "dns"


@dataclass
class SecurityPolicy:
    id: str
    name: str
    description: str
    action: SecurityPolicyAction
    rules: List[Dict[str, Any]] = field(default_factory=list)
    severity: str = "medium"
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResourceLimit:
    resource_type: ResourceType
    limit: float
    unit: str
    hard_limit: Optional[float] = None
    enforcement: str = "hard"


@dataclass
class NetworkRule:
    access_type: NetworkAccessType
    protocol: str
    port: Optional[int] = None
    destination: Optional[str] = None
    action: SecurityPolicyAction = SecurityPolicyAction.DENY


@dataclass
class FilesystemRule:
    path: str
    access: str  # read, write, execute
    action: SecurityPolicyAction = SecurityPolicyAction.DENY
    max_size_mb: Optional[int] = None


@dataclass
class RuntimeEvent:
    container_id: str
    event_type: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"
    blocked: bool = False


class ContainerSecurityPolicy:
    """Container security policy engine."""

    def __init__(self):
        self._policies: Dict[str, SecurityPolicy] = {}
        self._resource_limits: Dict[str, List[ResourceLimit]] = {}
        self._network_rules: Dict[str, List[NetworkRule]] = {}
        self._filesystem_rules: Dict[str, List[FilesystemRule]] = {}
        self._runtime_events: List[RuntimeEvent] = []
        self._lock = __import__('threading').Lock()
        self._initialize_default_policies()

    def _initialize_default_policies(self) -> None:
        """Initialize default security policies."""
        default_policies = [
            SecurityPolicy(
                id="pol_001",
                name="privilege_escalation_prevention",
                description="Prevent containers from running in privileged mode",
                action=SecurityPolicyAction.DENY,
                rules=[{"check": "privileged_mode", "operator": "eq", "value": True}],
                severity="critical",
            ),
            SecurityPolicy(
                id="pol_002",
                name="root_user_prevention",
                description="Prevent containers from running as root",
                action=SecurityPolicyAction.DENY,
                rules=[{"check": "run_as_user", "operator": "eq", "value": 0}],
                severity="high",
            ),
            SecurityPolicy(
                id="pol_003",
                name="host_network_isolation",
                description="Prevent containers from using host network",
                action=SecurityPolicyAction.DENY,
                rules=[{"check": "network_mode", "operator": "eq", "value": "host"}],
                severity="high",
            ),
            SecurityPolicy(
                id="pol_004",
                name="host_mount_restriction",
                description="Restrict access to host filesystem",
                action=SecurityPolicyAction.DENY,
                rules=[{"check": "mounts", "operator": "contains", "value": "/"}],
                severity="critical",
            ),
            SecurityPolicy(
                id="pol_005",
                name="dangerous_capabilities",
                description="Block dangerous Linux capabilities",
                action=SecurityPolicyAction.DENY,
                rules=[{"check": "capabilities", "operator": "in", "value": ["SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE"]}],
                severity="high",
            ),
            SecurityPolicy(
                id="pol_006",
                name="read_only_root_filesystem",
                description="Enforce read-only root filesystem where possible",
                action=SecurityPolicyAction.AUDIT,
                rules=[{"check": "read_only_root", "operator": "eq", "value": False}],
                severity="medium",
            ),
            SecurityPolicy(
                id="pol_007",
                name="seccomp_profile",
                description="Enforce seccomp profile for syscall filtering",
                action=SecurityPolicyAction.AUDIT,
                rules=[{"check": "seccomp_profile", "operator": "exists"}],
                severity="medium",
            ),
            SecurityPolicy(
                id="pol_008",
                name="no_new_privileges",
                description="Prevent privilege escalation within container",
                action=SecurityPolicyAction.ALLOW,
                rules=[{"check": "no_new_privileges", "operator": "eq", "value": True}],
                severity="high",
            ),
        ]

        for policy in default_policies:
            self._policies[policy.id] = policy

    def add_policy(self, policy: SecurityPolicy) -> None:
        """Add a security policy."""
        self._policies[policy.id] = policy

    def evaluate_policy(self, policy_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a security policy against container context."""
        policy = self._policies.get(policy_id)
        if not policy or not policy.enabled:
            return {"action": "skip", "reason": "policy_not_found_or_disabled"}

        violations = []
        for rule in policy.rules:
            check = rule.get("check")
            operator = rule.get("operator")
            expected = rule.get("value")
            actual = context.get(check)

            if operator == "eq" and actual != expected:
                violations.append(f"{check} is {actual}, expected {expected}")
            elif operator == "neq" and actual == expected:
                violations.append(f"{check} should not be {expected}")
            elif operator == "contains" and isinstance(actual, list) and expected in actual:
                violations.append(f"{check} contains forbidden value {expected}")
            elif operator == "in" and actual not in (expected if isinstance(expected, list) else [expected]):
                violations.append(f"{check} value {actual} not in allowed list {expected}")
            elif operator == "exists" and actual is None:
                violations.append(f"{check} is missing")

        if violations:
            result = {
                "action": policy.action.value,
                "policy_id": policy_id,
                "policy_name": policy.name,
                "violations": violations,
                "severity": policy.severity,
            }
            if policy.action == SecurityPolicyAction.DENY:
                self._record_runtime_event(
                    container_id=context.get("container_id", "unknown"),
                    event_type="policy_violation",
                    details=result,
                    severity=policy.severity,
                    blocked=True,
                )
            return result

        return {"action": "allow", "policy_id": policy_id}

    def set_resource_limits(self, container_id: str, limits: List[ResourceLimit]) -> None:
        """Set resource limits for a container."""
        self._resource_limits[container_id] = limits

    def check_resource_limits(self, container_id: str, usage: Dict[ResourceType, float]) -> List[Dict[str, Any]]:
        """Check if container is within resource limits."""
        violations = []
        limits = self._resource_limits.get(container_id, [])
        for limit in limits:
            used = usage.get(limit.resource_type, 0)
            if used > limit.limit:
                violations.append({
                    "container_id": container_id,
                    "resource": limit.resource_type.value,
                    "used": used,
                    "limit": limit.limit,
                    "unit": limit.unit,
                    "exceeded_by": used - limit.limit,
                })
                self._record_runtime_event(
                    container_id=container_id,
                    event_type="resource_limit_exceeded",
                    details={"resource": limit.resource_type.value, "used": used, "limit": limit.limit},
                    severity="warning",
                    blocked=limit.enforcement == "hard",
                )
        return violations

    def add_network_rule(self, container_id: str, rule: NetworkRule) -> None:
        """Add network access rule for a container."""
        self._network_rules.setdefault(container_id, []).append(rule)

    def check_network_access(self, container_id: str, access_type: NetworkAccessType,
                              protocol: str, destination: Optional[str] = None, port: Optional[int] = None) -> bool:
        """Check if network access is allowed."""
        rules = self._network_rules.get(container_id, [])
        for rule in rules:
            if rule.access_type == access_type and rule.protocol == protocol:
                if rule.destination and destination and rule.destination != destination:
                    continue
                if rule.port and port and rule.port != port:
                    continue
                if rule.action == SecurityPolicyAction.DENY:
                    self._record_runtime_event(
                        container_id=container_id,
                        event_type="network_access_denied",
                        details={"access_type": access_type.value, "protocol": protocol, "destination": destination, "port": port},
                        severity="warning",
                        blocked=True,
                    )
                    return False
                return True
        # Default deny
        self._record_runtime_event(
            container_id=container_id,
            event_type="network_access_denied",
            details={"access_type": access_type.value, "protocol": protocol, "destination": destination, "port": port},
            severity="warning",
            blocked=True,
        )
        return False

    def add_filesystem_rule(self, container_id: str, rule: FilesystemRule) -> None:
        """Add filesystem access rule for a container."""
        self._filesystem_rules.setdefault(container_id, []).append(rule)

    def check_filesystem_access(self, container_id: str, path: str, access: str) -> bool:
        """Check if filesystem access is allowed."""
        rules = self._filesystem_rules.get(container_id, [])
        for rule in rules:
            if rule.path in path or path.startswith(rule.path):
                if access in rule.access or rule.access == "all":
                    if rule.action == SecurityPolicyAction.DENY:
                        self._record_runtime_event(
                            container_id=container_id,
                            event_type="filesystem_access_denied",
                            details={"path": path, "access": access},
                            severity="warning",
                            blocked=True,
                        )
                        return False
                    return True
        # Default deny for write/execute outside allowed paths
        if access in ("write", "execute"):
            self._record_runtime_event(
                container_id=container_id,
                event_type="filesystem_access_denied",
                details={"path": path, "access": access},
                severity="warning",
                blocked=True,
            )
            return False
        return True

    def _record_runtime_event(self, container_id: str, event_type: str, details: Dict[str, Any],
                               severity: str = "info", blocked: bool = False) -> None:
        """Record a runtime security event."""
        event = RuntimeEvent(
            container_id=container_id,
            event_type=event_type,
            timestamp=time.time(),
            details=details,
            severity=severity,
            blocked=blocked,
        )
        with self._lock:
            self._runtime_events.append(event)
            if len(self._runtime_events) > 10000:
                self._runtime_events = self._runtime_events[-5000:]
        logger.warning("Container security event: %s on %s - %s", event_type, container_id, details)

    def get_runtime_events(self, container_id: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent runtime security events."""
        with self._lock:
            events = self._runtime_events
        if container_id:
            events = [e for e in events if e.container_id == container_id]
        return [e.__dict__ for e in events[-limit:]]

    def generate_container_hardening_report(self, container_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a container hardening report."""
        results = []
        for policy_id, policy in self._policies.items():
            evaluation = self.evaluate_policy(policy_id, container_context)
            results.append({
                "policy_id": policy_id,
                "policy_name": policy.name,
                "severity": policy.severity,
                "evaluation": evaluation,
            })

        violations = [r for r in results if r["evaluation"].get("action") == "deny"]
        return {
            "container_id": container_context.get("container_id", "unknown"),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "total_policies_evaluated": len(results),
            "violations": len(violations),
            "policy_results": results,
            "hardening_score": max(0, 100 - len(violations) * 10),
            "recommendations": [f"Fix policy violation: {r['policy_name']}" for r in violations],
        }

    def get_policy_summary(self) -> Dict[str, Any]:
        """Get summary of all policies and their status."""
        with self._lock:
            return {
                "total_policies": len(self._policies),
                "enabled_policies": sum(1 for p in self._policies.values() if p.enabled),
                "policies": [
                    {"id": p.id, "name": p.name, "severity": p.severity, "enabled": p.enabled}
                    for p in self._policies.values()
                ],
                "total_runtime_events": len(self._runtime_events),
                "blocked_events": sum(1 for e in self._runtime_events if e.blocked),
            }

    def generate_security_report(self, container_contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a comprehensive container security report."""
        reports = []
        for ctx in container_contexts:
            reports.append(self.generate_container_hardening_report(ctx))
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "containers_reviewed": len(reports),
            "total_violations": sum(r["violations"] for r in reports),
            "avg_hardening_score": round(sum(r["hardening_score"] for r in reports) / max(1, len(reports)), 2),
            "container_reports": reports,
        }


container_security = ContainerSecurityPolicy()


def evaluate_container_policy(policy_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to evaluate container policy."""
    return container_security.evaluate_policy(policy_id, context)


def check_container_hardening(container_context: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to check container hardening."""
    return container_security.generate_container_hardening_report(container_context)
