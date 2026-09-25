"""Progressive delivery pipelines for canary, blue-green, and feature flags."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeploymentStrategy(str, Enum):
    ROLLING = "rolling"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    A_B_TESTING = "a_b_testing"
    SHADOW = "shadow"


class TrafficSplit(str, Enum):
    PERCENT = "percent"
    HEADER = "header"
    COOKIE = "cookie"
    QUERY = "query"


@dataclass
class CanaryConfig:
    steps: List[Dict[str, int]]
    analysis_interval: int = 60
    analysis_interval_count: int = 5
    success_threshold: int = 90
    max_unavailable: int = 1


@dataclass
class BlueGreenConfig:
    active_service: str
    preview_service: str
    preview_host: str
    auto_promote: bool = False
    promotion_interval: int = 300


@dataclass
class FeatureFlag:
    key: str
    enabled: bool = False
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProgressiveDeliveryManager:
    """Manage progressive delivery pipelines."""

    def __init__(self) -> None:
        self._canary_configs: Dict[str, CanaryConfig] = {}
        self._blue_green_configs: Dict[str, BlueGreenConfig] = {}
        self._feature_flags: Dict[str, FeatureFlag] = {}
        self._analysis_results: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("Progressive delivery manager initialized")

    def register_canary(self, service_name: str, config: CanaryConfig) -> None:
        self._canary_configs[service_name] = config
        logger.info("Registered canary config for %s", service_name)

    def register_blue_green(self, service_name: str, config: BlueGreenConfig) -> None:
        self._blue_green_configs[service_name] = config
        logger.info("Registered blue-green config for %s", service_name)

    def register_feature_flag(self, flag: FeatureFlag) -> None:
        self._feature_flags[flag.key] = flag
        logger.info("Registered feature flag: %s (enabled=%s)", flag.key, flag.enabled)

    def is_enabled(self, flag_key: str, default: bool = False) -> bool:
        flag = self._feature_flags.get(flag_key)
        if not flag:
            return default
        return flag.enabled

    def set_feature_flag(self, flag_key: str, enabled: bool) -> None:
        flag = self._feature_flags.get(flag_key)
        if not flag:
            raise KeyError(f"Feature flag not found: {flag_key}")
        flag.enabled = enabled
        flag.updated_at = time.time()
        logger.info("Feature flag %s set to %s", flag_key, enabled)

    def get_feature_flag(self, flag_key: str) -> Optional[FeatureFlag]:
        return self._feature_flags.get(flag_key)

    def list_feature_flags(self) -> List[FeatureFlag]:
        return list(self._feature_flags.values())

    def get_canary_steps(self, service_name: str) -> List[Dict[str, int]]:
        config = self._canary_configs.get(service_name)
        if not config:
            return []
        return config.steps

    def validate_canary_traffic(self, service_name: str, step_index: int) -> bool:
        config = self._canary_configs.get(service_name)
        if not config or step_index >= len(config.steps):
            return False
        return config.steps[step_index].get("percent", 0) > 0

    def record_analysis(self, service_name: str, result: Dict[str, Any]) -> None:
        if service_name not in self._analysis_results:
            self._analysis_results[service_name] = []
        self._analysis_results[service_name].append(result)
        logger.info("Recorded analysis result for %s: %s", service_name, result)

    def get_analysis_results(self, service_name: str) -> List[Dict[str, Any]]:
        return self._analysis_results.get(service_name, [])

    def should_promote(self, service_name: str) -> bool:
        results = self._analysis_results.get(service_name, [])
        if not results:
            return False
        recent = results[-5:]
        success_rate = sum(1 for r in recent if r.get("success")) / len(recent) * 100
        return success_rate >= 90

    def promote_to_production(self, service_name: str) -> bool:
        if not self.should_promote(service_name):
            return False
        config = self._blue_green_configs.get(service_name)
        if not config:
            return False
        config.active_service = config.preview_service
        logger.info("Promoted %s to production", service_name)
        return True

    def generate_istio_destination_rule(self, service_name: str, subset: str = "v1") -> str:
        return f"""\
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: {service_name}
  namespace: astrovox-production
spec:
  host: {service_name}
  subsets:
  - name: {subset}
    selector:
      app: {service_name}
    trafficPolicy:
      loadBalancer:
        simple: ROUND_ROBIN
      connectionPool:
        tcp:
          maxConnections: 10
        http:
          h1MaxPendingRequests: 10
      outlierDetection:
        consecutive5xxErrors: 5
        interval: 10s
        baseEjectionTime: 30s
"""

    def generate_istio_virtual_service(self, service_name: str, steps: List[Dict[str, int]]) -> str:
        routes = []
        for step in steps:
            weight = step.get("percent", 0)
            routes.append(f"""\
        - destination:
            host: {service_name}
          weight: {weight}""")
        routes_str = "\n".join(routes)
        return f"""\
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: {service_name}
  namespace: astrovox-production
spec:
  hosts:
  - {service_name}
  http:
  - route:
{routes_str}
"""


_progressive_delivery: Optional[ProgressiveDeliveryManager] = None


def get_progressive_delivery_manager() -> ProgressiveDeliveryManager:
    global _progressive_delivery
    if _progressive_delivery is None:
        _progressive_delivery = ProgressiveDeliveryManager()
    return _progressive_delivery
