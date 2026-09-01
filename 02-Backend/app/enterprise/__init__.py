"""Enterprise Module — organizations, workspaces, RBAC, real-time, notifications."""

from .models import (
    Organization,
    Workspace,
    OrganizationMembership,
    WorkspaceMembership,
    ORG_ROLES,
    WORKSPACE_ROLES,
)
from .service import org_service, OrganizationService
from .rbac import rbac, RBACEnforcer
from .websocket import ws_manager, ConnectionManager
from .notifications import notification_service, NotificationService
from .search import EnterpriseSearch, SearchResult

__all__ = [
    "Organization",
    "Workspace",
    "OrganizationMembership",
    "WorkspaceMembership",
    "ORG_ROLES",
    "WORKSPACE_ROLES",
    "org_service",
    "OrganizationService",
    "rbac",
    "RBACEnforcer",
    "ws_manager",
    "ConnectionManager",
    "notification_service",
    "NotificationService",
    "EnterpriseSearch",
    "SearchResult",
]
