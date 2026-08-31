"""Shared models and constants used across the application."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ============================================================================
# Roles & Permissions
# ============================================================================

class Role(Enum):
    """User roles for RBAC."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    ORG_ADMIN = "org_admin"
    VIEWER = "viewer"


class Permission(Enum):
    """System permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_ORG = "manage_org"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_API_KEYS = "manage_api_keys"
    ADMIN = "admin"


ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.VIEWER: [Permission.READ],
    Role.USER: [Permission.READ, Permission.WRITE],
    Role.MODERATOR: [Permission.READ, Permission.WRITE, Permission.DELETE],
    Role.ADMIN: [
        Permission.READ, Permission.WRITE, Permission.DELETE,
        Permission.MANAGE_USERS, Permission.MANAGE_SETTINGS,
        Permission.VIEW_ANALYTICS, Permission.MANAGE_API_KEYS,
    ],
    Role.ORG_ADMIN: [
        Permission.READ, Permission.WRITE, Permission.DELETE,
        Permission.MANAGE_USERS, Permission.MANAGE_ORG,
        Permission.VIEW_ANALYTICS, Permission.MANAGE_API_KEYS,
    ],
}


# ============================================================================
# Model Costs (USD per 1K tokens)
# ============================================================================

MODEL_COSTS: dict[str, dict[str, float]] = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-1.0-pro": {"input": 0.0005, "output": 0.0015},
    "llama3": {"input": 0, "output": 0},
    "llama3.1": {"input": 0, "output": 0},
    "mistral": {"input": 0, "output": 0},
    "mixtral": {"input": 0, "output": 0},
    "codellama": {"input": 0, "output": 0},
    "phi3": {"input": 0, "output": 0},
    "gemma2": {"input": 0, "output": 0},
}


# ============================================================================
# Shared Dataclasses
# ============================================================================

@dataclass
class EmbeddingVector:
    """Result from an embedding request."""
    vector: list[float]
    model: str
    tokens_used: Optional[int] = None
