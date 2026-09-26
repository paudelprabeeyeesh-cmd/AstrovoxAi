from typing import Any, Dict, List
from dataclasses import dataclass
from ..deployment.base_adapter import BaseCloudAdapter


@dataclass
class RegionConfig:
    region: str
    primary: bool = False
    instances: int = 1
    storage_replication: bool = True


class MultiRegionDeployment:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.regions: List[RegionConfig] = []

    def add_region(self, config: RegionConfig) -> None:
        self.regions.append(config)

    def deploy_all(self) -> Dict[str, Any]:
        results = []
        for region_config in self.regions:
            result = self.adapter.setup_multi_region(
                [r.region for r in self.regions],
                next((r.region for r in self.regions if r.primary), self.regions[0].region),
            )
            results.append(result)
        return {
            "status": "deployed",
            "regions": [r.region for r in self.regions],
            "results": results,
        }

    def configure_replication(self, source_bucket: str, destination_buckets: List[str]) -> Dict[str, Any]:
        return {
            "status": "configured",
            "source_bucket": source_bucket,
            "destination_buckets": destination_buckets,
        }

    def setup_global_load_balancer(self, lb_name: str, regions: List[str]) -> Dict[str, Any]:
        return self.adapter.configure_load_balancer(lb_name, [])
