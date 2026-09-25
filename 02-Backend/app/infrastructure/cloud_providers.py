"""Cloud provider configuration."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


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
