"""Enterprise admin panel."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AdminUser:
    user_id: str
    email: str
    role: str = "admin"
    permissions: List[str] = field(default_factory=list)
    last_login: Optional[float] = None
    mfa_enabled: bool = False


@dataclass
class SystemMetrics:
    timestamp: float = field(default_factory=time.time)
    active_users: int = 0
    api_calls_24h: int = 0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_revenue_usd: float = 0.0
    storage_used_mb: float = 0.0


class EnterpriseAdminPanel:
    """Enterprise admin panel with metrics, user management, and system controls."""

    def __init__(self):
        self._admins: Dict[str, AdminUser] = {}
        self._metrics_history: List[SystemMetrics] = []
        self._feature_flags: Dict[str, bool] = {}
        self._maintenance_mode: bool = False

    def register_admin(self, admin: AdminUser) -> None:
        self._admins[admin.user_id] = admin
        logger.info("Registered admin user: %s", admin.email)

    def get_admin(self, user_id: str) -> Optional[AdminUser]:
        return self._admins.get(user_id)

    def list_admins(self) -> List[AdminUser]:
        return list(self._admins.values())

    def record_metrics(self, metrics: SystemMetrics) -> None:
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > 1000:
            self._metrics_history = self._metrics_history[-1000:]

    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        return self._metrics_history[-1] if self._metrics_history else None

    def get_metrics_history(self, minutes: int = 60) -> List[SystemMetrics]:
        cutoff = time.time() - (minutes * 60)
        return [m for m in self._metrics_history if m.timestamp >= cutoff]

    def set_feature_flag(self, flag_name: str, enabled: bool) -> None:
        self._feature_flags[flag_name] = enabled
        logger.info("Feature flag %s set to %s", flag_name, enabled)

    def get_feature_flag(self, flag_name: str) -> bool:
        return self._feature_flags.get(flag_name, False)

    def list_feature_flags(self) -> Dict[str, bool]:
        return dict(self._feature_flags)

    def enable_maintenance_mode(self) -> None:
        self._maintenance_mode = True
        logger.warning("Maintenance mode enabled")

    def disable_maintenance_mode(self) -> None:
        self._maintenance_mode = False
        logger.info("Maintenance mode disabled")

    def is_maintenance_mode(self) -> bool:
        return self._maintenance_mode

    def get_system_health(self) -> Dict[str, Any]:
        latest = self.get_latest_metrics()
        return {
            "maintenance_mode": self._maintenance_mode,
            "active_admins": len(self._admins),
            "metrics_available": latest is not None,
            "latest_metrics": latest.__dict__ if latest else None,
        }


enterprise_admin = EnterpriseAdminPanel()
