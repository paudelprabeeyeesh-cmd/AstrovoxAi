import time
import threading
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class Region(Enum):
    US_EAST = "us-east-1"
    US_WEST = "us-west-2"
    EU_WEST = "eu-west-1"
    AP_SOUTHEAST = "ap-southeast-1"


@dataclass
class ClusterNode:
    cluster_id: str
    region: Region
    endpoint: str
    is_healthy: bool = True
    latency_ms: float = 0.0
    load: float = 0.0
    last_health_check: float = field(default_factory=time.time)


@dataclass
class RoutingDecision:
    cluster_id: str
    region: Region
    endpoint: str
    reason: str
    fallback_used: bool = False


class RegionalRouter:
    def __init__(
        self,
        allowed_regions: Optional[Set[Region]] = None,
        residency_constraints: Optional[Dict[str, Set[Region]]] = None,
    ):
        self._clusters: Dict[str, ClusterNode] = {}
        self._region_clusters: Dict[Region, List[str]] = {r: [] for r in Region}
        self._allowed_regions = allowed_regions or set(Region)
        self._residency_constraints = residency_constraints or {}
        self._lock = threading.Lock()
        self._failover_order: Dict[str, List[str]] = {}

    def register_cluster(self, node: ClusterNode):
        with self._lock:
            self._clusters[node.cluster_id] = node
            self._region_clusters[node.region].append(node.cluster_id)

    def set_failover_order(self, primary_id: str, fallback_ids: List[str]):
        with self._lock:
            self._failover_order[primary_id] = fallback_ids

    def _get_nearest_cluster(
        self, client_region: Optional[Region] = None
    ) -> Optional[ClusterNode]:
        candidates = []
        for cluster in self._clusters.values():
            if not cluster.is_healthy or cluster.region not in self._allowed_regions:
                continue
            dist = self._distance_score(client_region, cluster.region)
            candidates.append((dist, cluster.latency_ms, cluster.load, cluster))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1], x[2]))
        return candidates[0][3]

    def _distance_score(
        self, client_region: Optional[Region], cluster_region: Region
    ) -> int:
        if client_region is None:
            return 0
        if client_region == cluster_region:
            return 0
        region_groups = {
            frozenset([Region.US_EAST, Region.US_WEST]): 1,
            frozenset([Region.EU_WEST]): 2,
            frozenset([Region.AP_SOUTHEAST]): 3,
        }
        for group, score in region_groups.items():
            if client_region in group and cluster_region in group:
                return score
        return 4

    def _check_residency(self, tenant_id: str, region: Region) -> bool:
        allowed = self._residency_constraints.get(tenant_id)
        if allowed is None:
            return True
        return region in allowed

    def route(
        self, client_region: Optional[Region] = None, tenant_id: str = "default"
    ) -> RoutingDecision:
        with self._lock:
            healthy = [
                c for c in self._clusters.values()
                if c.is_healthy and c.region in self._allowed_regions
            ]
            if not healthy:
                return RoutingDecision(
                    cluster_id="",
                    region=Region.US_EAST,
                    endpoint="",
                    reason="no_healthy_clusters",
                    fallback_used=True,
                )

            eligible = [
                c for c in healthy
                if self._check_residency(tenant_id, c.region)
            ]
            if not eligible:
                eligible = healthy

            candidates = sorted(
                eligible,
                key=lambda c: (
                    self._distance_score(client_region, c.region),
                    c.latency_ms,
                    c.load,
                ),
            )

            chosen = candidates[0]
            candidates[1] if len(candidates) > 1 else None
            return RoutingDecision(
                cluster_id=chosen.cluster_id,
                region=chosen.region,
                endpoint=chosen.endpoint,
                reason=f"nearest_healthy_{chosen.region.value}",
                fallback_used=False,
            )

    def get_fallback(self, primary_id: str) -> Optional[RoutingDecision]:
        with self._lock:
            fallback_ids = self._failover_order.get(primary_id, [])
            for fid in fallback_ids:
                node = self._clusters.get(fid)
                if node and node.is_healthy:
                    return RoutingDecision(
                        cluster_id=node.cluster_id,
                        region=node.region,
                        endpoint=node.endpoint,
                        reason=f"failover_from_{primary_id}",
                        fallback_used=True,
                    )
            return None
