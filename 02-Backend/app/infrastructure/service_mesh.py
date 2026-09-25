"""Service mesh configuration for Istio and Linkerd."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MeshProvider(str, Enum):
    ISTIO = "istio"
    LINKERD = "linkerd"
    CONSUL = "consul"
    NGINX = "nginx"


class TrafficPolicy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_REQUEST = "least_request"
    RANDOM = "random"
    PASSTHROUGH = "passthrough"


class OutlierDetection(str, Enum):
    CONSECUTIVE_GATEWAY_ERRORS = "consecutive_gateway_errors"
    CONSECUTIVE_5XX = "consecutive_5xx"
    INTERVAL_GATEWAY_ERRORS = "interval_gateway_errors"


@dataclass
class VirtualServiceHost:
    name: str
    gateway: str = "astrovox-gateway"
    http_ports: List[int] = field(default_factory=lambda: [80, 443])
    tls_mode: str = "SIMPLE"


@dataclass
class DestinationRuleHost:
    name: str
    traffic_policy: TrafficPolicy = TrafficPolicy.ROUND_ROBIN
    connection_pool_size: int = 10
    circuit_breaker_errors: int = 5
    outlier_detection_enabled: bool = True


@dataclass
class SidecarConfig:
    egress: List[str] = field(default_factory=lambda: ["*"])
    ingress: List[str] = field(default_factory=lambda: ["*"])
    outbound_traffic_policy: str = "ALLOW_ANY"


@dataclass
class ServiceMeshConfig:
    mesh_id: str
    provider: MeshProvider
    namespace: str = "astrovox-production"
    version: str = "1.20.0"
    control_plane: str = "standard"
    sidecar_injection: bool = True
    sidecar_resources: Dict[str, str] = field(default_factory=dict)
    telemetry_enabled: bool = True
    mTLS_mode: str = "PERMISSIVE"
    default_traffic_policy: TrafficPolicy = TrafficPolicy.ROUND_ROBIN


class ServiceMeshManager:
    """Manage service mesh configurations for Istio/Linkerd."""

    def __init__(self, config: ServiceMeshConfig) -> None:
        self._config = config
        self._virtual_services: Dict[str, VirtualServiceHost] = {}
        self._destination_rules: Dict[str, DestinationRuleHost] = {}
        self._sidecars: Dict[str, SidecarConfig] = {}
        logger.info("Service mesh manager initialized for %s", config.provider.value)

    def register_virtual_service(self, vs: VirtualServiceHost) -> None:
        self._virtual_services[vs.name] = vs
        logger.debug("Registered virtual service: %s", vs.name)

    def register_destination_rule(self, dr: DestinationRuleHost) -> None:
        self._destination_rules[dr.name] = dr
        logger.debug("Registered destination rule: %s", dr.name)

    def register_sidecar(self, name: str, config: SidecarConfig) -> None:
        self._sidecars[name] = config
        logger.debug("Registered sidecar: %s", name)

    def generate_istio_virtual_service(self, name: str) -> str:
        vs = self._virtual_services.get(name)
        if not vs:
            raise ValueError(f"Virtual service not found: {name}")
        ports = ",".join(str(p) for p in vs.http_ports)
        return f"""\
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: {name}
  namespace: {self._config.namespace}
spec:
  hosts:
  - {vs.name}
  gateways:
  - {vs.gateway}
  http:
  - route:
    - destination:
        host: {name}
    timeout: 30s
    retries:
      attempts: 3
      perTryTimeout: 10s
      retryOn: gateway-error,connect-failure,refused-stream
"""

    def generate_istio_destination_rule(self, name: str) -> str:
        dr = self._destination_rules.get(name)
        if not dr:
            raise ValueError(f"Destination rule not found: {name}")
        return f"""\
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: {name}
  namespace: {self._config.namespace}
spec:
  host: {name}
  trafficPolicy:
    loadBalancer:
      simple: {dr.traffic_policy.value.upper()}
    connectionPool:
      tcp:
        maxConnections: {dr.connection_pool_size}
      http:
        h1MaxPendingRequests: {dr.connection_pool_size}
        http2MaxRequests: {dr.connection_pool_size}
    outlierDetection:
      consecutive5xxErrors: {dr.circuit_breaker_errors}
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
"""

    def generate_linkerd_service_profile(self, name: str) -> str:
        return f"""\
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: {name}
  namespace: {self._config.namespace}
spec:
  # ...
  routes:
  - name: default
    condition:
      method: GET
      pathRegex: /.*
    # ...
"""

    def generate_sidecar_injection_label(self) -> Dict[str, str]:
        if self._config.provider == MeshProvider.ISTIO:
            return {"istio-injection": "enabled"}
        if self._config.provider == MeshProvider.LINKERD:
            return {"linkerd.io/inject": "enabled"}
        return {}

    def get_config(self) -> ServiceMeshConfig:
        return self._config

    def list_virtual_services(self) -> List[str]:
        return list(self._virtual_services.keys())

    def list_destination_rules(self) -> List[str]:
        return list(self._destination_rules.keys())


_mesh_manager: Optional[ServiceMeshManager] = None


def get_mesh_manager() -> ServiceMeshManager:
    global _mesh_manager
    if _mesh_manager is None:
        _mesh_manager = ServiceMeshManager(
            config=ServiceMeshConfig(
                mesh_id="astrovox-mesh",
                provider=MeshProvider.ISTIO,
                namespace="astrovox-production",
            )
        )
    return _mesh_manager
