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
from .abac import abac, ABACEnforcer, ABACContext
from .websocket import ws_manager, ConnectionManager
from .notifications import notification_service, NotificationService
from .search import EnterpriseSearch, SearchResult
from .tenancy import tenant_manager, TenantManager, tenant_required, tenant_scoped
from .encryption import tenant_encryption, TenantEncryptionManager

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
    "abac",
    "ABACEnforcer",
    "ABACContext",
    "ws_manager",
    "ConnectionManager",
    "notification_service",
    "NotificationService",
    "EnterpriseSearch",
    "SearchResult",
    "tenant_manager",
    "TenantManager",
    "tenant_required",
    "tenant_scoped",
    "tenant_encryption",
    "TenantEncryptionManager",
]
