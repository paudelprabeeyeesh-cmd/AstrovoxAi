from __future__ import annotations

__all__ = [
    "annotations",
    "LookupPermission",
    "AstrovoxClient",
]

"""Ecosystem platform: plugins, registry, lookup, compatibility, recovery, validation, dashboard, SDK, webhooks, integrations."""

from .registry import (
    CompatibilityMatrix,
    EcosystemRegistry,
    EntityKind,
    RegistryEntry,
    TrustLevel,
    get_ecosystem_registry,
)
from .lookup import LookupPermission, LookupProvider, LookupResult, UniversalLookupEngine, get_lookup_engine
from .compatibility import (
    CompatibilityReport,
    ResourceRequirement,
    SecurityPolicy,
    VersionRequirement,
    check_api_compatibility,
    check_dependencies,
    check_security_policy,
    evaluate_compatibility,
    satisfies_resource,
    satisfies_version,
)
from .recovery import (
    OperationRecord,
    OperationStatus,
    RecoveryReport,
    RecoveryRollbackFramework,
    TransactionLogEntry,
    get_recovery_framework,
)
from .validation import (
    ContinuousValidator,
    ValidationResult,
    ValidationStatus,
    ValidationType,
    get_continuous_validator,
)
from .dashboard import (
    AuditEvent,
    CompatibilityWarning,
    HealthStatus,
    OperationalDashboard,
    PerformanceMetric,
    PluginStatus,
    SecurityAlert,
    WorkflowStatus,
    get_dashboard,
)
from .extension_sdk import (
    CompilerAPI,
    EventAPI,
    ExtensionSDK,
    PluginAPI,
    RuntimeAPI,
    SDKContext,
    StorageAPI,
    WorkflowAPI,
)
from .sdk import AstrovoxClient, AstrovoxError
