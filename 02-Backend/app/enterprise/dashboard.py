"""Admin dashboard APIs."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from dataclasses import dataclass, field

from .tenancy import tenant_manager
from .audit import audit_exporter
from ..retention import retention_engine
from .compliance import compliance_generator
from .partners import partner_service
from .sso import SSOManager as enterprise_sso

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetric:
    metric_id: str
    tenant_id: str
    name: str
    value: float
    unit: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    recorded_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp)


class AdminDashboardAPI:
    def get_tenant_overview(self, tenant_id: str) -> Dict[str, Any]:
        tenant = tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}
        return {
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "plan": tenant.plan,
            "is_active": tenant.is_active,
            "data_residency": tenant.data_residency,
        }

    def list_all_tenants(self) -> List[Dict[str, Any]]:
        return tenant_manager.list_tenants()

    def get_system_health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "tenant_count": len(tenant_manager.tenants),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_audit_summary(self, tenant_id: str, days: int = 7) -> Dict[str, Any]:
        start = datetime.now(timezone.utc) - timedelta(days=days)
        result = audit_exporter.export(
            requester_id=tenant_id,
            format="json",
            filters={"start_date": start.isoformat()},
        )
        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "total_events": result.get("rows_exported", 0),
            "tamper_evidence": result.get("tamper_evidence", {}),
        }

    def get_compliance_status(self, tenant_id: str) -> Dict[str, Any]:
        reports = []
        for report_id, report in list(compliance_generator._reports.items()):
            if report.tenant_id == tenant_id:
                reports.append({
                    "report_id": report.report_id,
                    "framework": report.framework,
                    "status": report.status,
                    "generated_at": report.generated_at.isoformat(),
                })
        return {"tenant_id": tenant_id, "reports": reports}

    def get_retention_status(self) -> Dict[str, Any]:
        return {
            "policies": retention_engine.list_policies(),
        }

    def get_billing_summary(self, tenant_id: str, period: str = "monthly") -> Dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "period": period,
            "estimated_cost": 0.0,
            "currency": "USD",
        }

    def get_partner_activity(self, tenant_id: str = None) -> List[Dict[str, Any]]:
        partners = partner_service.list_partners(tenant_id=tenant_id)
        return [
            {
                "id": p.id,
                "name": p.name,
                "scopes": p.scopes,
                "is_active": p.is_active,
            }
            for p in partners
        ]

    def get_sso_status(self, tenant_id: str) -> Dict[str, Any]:
        connections = enterprise_sso.list_connections(tenant_id)
        return {
            "tenant_id": tenant_id,
            "connections": [
                {
                    "connection_id": c.connection_id,
                    "provider_type": c.provider_type,
                    "is_active": c.is_active,
                }
                for c in connections
            ],
        }


admin_dashboard = AdminDashboardAPI()
