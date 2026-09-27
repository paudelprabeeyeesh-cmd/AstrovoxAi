"""
Enterprise module for AstrovoxAI.
Provides SSO/SAML authentication, audit logging, compliance reports, SLA guarantees, and private deployments.
"""

from .sso_saml import SSOManager, SAMLConfig
from .audit_logging import AuditLogger, AuditEvent, AuditLogQuery
from .compliance_reports import ComplianceReportGenerator, ComplianceReport, ComplianceFramework
from .sla_manager import SLAManager, SLAConfig, SLAStatus
from .private_deployments import PrivateDeploymentManager, PrivateDeployment, DeploymentConfig

__all__ = [
    "SSOManager",
    "SAMLConfig",
    "AuditLogger",
    "AuditEvent",
    "AuditLogQuery",
    "ComplianceReportGenerator",
    "ComplianceReport",
    "ComplianceFramework",
    "SLAManager",
    "SLAConfig",
    "SLAStatus",
    "PrivateDeploymentManager",
    "PrivateDeployment",
    "DeploymentConfig",
]
