"""Cloud provider configuration."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CloudProvider(Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    BARE_METAL = "bare_metal"
    EDGE = "edge"


@dataclass
class CloudRegion:
    region_id: str
    provider: CloudProvider
    name: str
    endpoints: List[str] = field(default_factory=list)
    zones: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CloudCluster:
    cluster_id: str
    provider: CloudProvider
    region: str
    name: str
    node_count: int = 3
    gpu_nodes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CloudProviderManager:
    """Manage cloud provider configurations."""

    _regions: Dict[str, CloudRegion] = {}
    _clusters: Dict[str, CloudCluster] = {}

    @classmethod
    def register_region(cls, region: CloudRegion) -> None:
        cls._regions[region.region_id] = region

    @classmethod
    def register_cluster(cls, cluster: CloudCluster) -> None:
        cls._clusters[cluster.cluster_id] = cluster

    @classmethod
    def get_clusters_by_provider(cls, provider: CloudProvider) -> List[CloudCluster]:
        return [c for c in cls._clusters.values() if c.provider == provider]


_cloud_manager: Optional[CloudProviderManager] = None


def get_cloud_manager() -> CloudProviderManager:
    global _cloud_manager
    if _cloud_manager is None:
        _cloud_manager = CloudProviderManager()
    return _cloud_manager
