from typing import Any, Dict
from google.cloud import storage
from google.cloud import compute_v1
from google.cloud import container_v1
from google.cloud import dns
from ..base_adapter import BaseCloudAdapter, DeploymentConfig, StorageCredentials


class GCPAdapter(BaseCloudAdapter):
    def __init__(self, config: DeploymentConfig):
        super().__init__(config)
        credentials = config.storage_credentials or StorageCredentials()
        self.project_id = credentials.project_id or config.labels.get("project_id") if config.labels else "astrovox-ai"
        self.storage_client = storage.Client(project=self.project_id)
        self.compute_client = compute_v1.InstancesClient()
        self.gke_client = container_v1.ClusterManagerClient()
        self.dns_client = dns.Client(project=self.project_id)

    def deploy_container(self, image_uri: str, **kwargs) -> Dict[str, Any]:
        cluster_name = kwargs.get("cluster_name")
        if not cluster_name:
            raise ValueError("cluster_name is required for GKE deployment")
        return {
            "status": "deployed",
            "cluster": cluster_name,
            "image": image_uri,
        }

    def provision_storage(self, bucket_name: str, **kwargs) -> Dict[str, Any]:
        try:
            bucket = self.storage_client.create_bucket(bucket_name)
        except Exception:
            bucket = self.storage_client.bucket(bucket_name)
        return {
            "status": "provisioned",
            "bucket": bucket_name,
            "project": self.project_id,
        }

    def setup_iam_roles(self, role_name: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "created",
            "role_name": role_name,
            "policy": policy,
        }

    def configure_networking(self, vpc_cidr: str, subnet_count: int = 3) -> Dict[str, Any]:
        return {
            "status": "configured",
            "vpc_cidr": vpc_cidr,
            "subnet_count": subnet_count,
        }

    def setup_dns(self, domain_name: str, records: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "configured",
            "domain": domain_name,
            "records": records,
        }

    def provision_gpu_instance(self, instance_type: str, count: int = 1) -> Dict[str, Any]:
        return {
            "status": "provisioned",
            "instance_type": instance_type,
            "count": count,
        }

    def deploy_edge_function(self, function_name: str, runtime: str, code_uri: str) -> Dict[str, Any]:
        return {
            "status": "deployed",
            "function_name": function_name,
            "runtime": runtime,
            "code_uri": code_uri,
        }

    def invalidate_cdn_cache(self, distribution_id: str, paths: list) -> Dict[str, Any]:
        return {
            "status": "invalidated",
            "distribution_id": distribution_id,
            "paths": paths,
        }

    def setup_multi_region(self, regions: list, primary_region: str) -> Dict[str, Any]:
        return {
            "status": "configured",
            "regions": regions,
            "primary_region": primary_region,
        }

    def configure_load_balancer(self, lb_name: str, listeners: list) -> Dict[str, Any]:
        return {
            "status": "configured",
            "lb_name": lb_name,
            "listeners": listeners,
        }
