"""Tool permissions and access control."""

from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ToolPermission(Enum):
    EXECUTE = "execute"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class ToolAccessPolicy:
    tool_name: str
    allowed_roles: Set[str] = field(default_factory=set)
    allowed_users: Set[str] = field(default_factory=set)
    allowed_ips: Set[str] = field(default_factory=set)
    max_concurrent: int = 5
    require_approval: bool = False


class ToolPermissionManager:
    _policies: Dict[str, ToolAccessPolicy] = {}
    _active_sessions: Dict[str, int] = {}

    @classmethod
    def register(cls, policy: ToolAccessPolicy) -> None:
        cls._policies[policy.tool_name] = policy

    @classmethod
    def check_permission(cls, tool_name: str, user_id: str, role: str, ip_address: str) -> bool:
        policy = cls._policies.get(tool_name)
        if not policy:
            return True
        if policy.allowed_roles and role not in policy.allowed_roles:
            return False
        if policy.allowed_users and user_id not in policy.allowed_users:
            return False
        if policy.allowed_ips and ip_address not in policy.allowed_ips:
            return False
        return True

    @classmethod
    def check_concurrent(cls, tool_name: str) -> bool:
        policy = cls._policies.get(tool_name)
        if not policy:
            return True
        current = cls._active_sessions.get(tool_name, 0)
        return current < policy.max_concurrent

    @classmethod
    def increment_session(cls, tool_name: str) -> None:
        cls._active_sessions[tool_name] = cls._active_sessions.get(tool_name, 0) + 1

    @classmethod
    def decrement_session(cls, tool_name: str) -> None:
        current = cls._active_sessions.get(tool_name, 0)
        cls._active_sessions[tool_name] = max(0, current - 1)
