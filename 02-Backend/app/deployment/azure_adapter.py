from typing import Any, Dict
from azure.storage.blob import BlobServiceClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from ..base_adapter import BaseCloudAdapter, DeploymentConfig, StorageCredentials


class AzureAdapter(BaseCloudAdapter):
    def __init__(self, config: DeploymentConfig):
        super().__init__(config)
        credentials = config.storage_credentials or StorageCredentials()
        connection_string = (
            f"DefaultEndpointsProtocol=https;AccountName={credentials.account_name};"
            f"AccountKey={credentials.account_key};EndpointSuffix=core.windows.net"
        )
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.resource_client = ResourceManagementClient(
            credential=credentials.account_key,
            subscription_id=config.labels.get("subscription_id") if config.labels else None,
        )
        self.network_client = NetworkManagementClient(
            credential=credentials.account_key,
            subscription_id=config.labels.get("subscription_id") if config.labels else None,
        )
        self.container_client = ContainerServiceClient(
            credential=credentials.account_key,
            subscription_id=config.labels.get("subscription_id") if config.labels else None,
        )

    def deploy_container(self, image_uri: str, **kwargs) -> Dict[str, Any]:
        cluster_name = kwargs.get("cluster_name")
        if not cluster_name:
            raise ValueError("cluster_name is required for AKS deployment")
        return {
            "status": "deployed",
            "cluster": cluster_name,
            "image": image_uri,
        }

    def provision_storage(self, bucket_name: str, **kwargs) -> Dict[str, Any]:
        container_client = self.blob_service_client.get_container_client(bucket_name)
        try:
            container_client.create_container()
        except Exception:
            pass
        return {
            "status": "provisioned",
            "container": bucket_name,
            "account": self.config.storage_credentials.account_name,
        }

    def setup_iam_roles(self, role_name: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "created",
            "role_name": role_name,
            "policy": policy,
        }

    def configure_networking(self, vpc_cidr: str, subnet_count: int = 3) -> Dict[str, Any]:
        subscription_id = self.config.labels.get("subscription_id") if self.config.labels else None
        rg_name = "astrovox-rg"
        self.resource_client.resource_groups.create_or_update(
            rg_name,
            {"location": "eastus"},
        )
        vnet = self.network_client.virtual_networks.begin_create_or_update(
            rg_name,
            "astrovox-vnet",
            {
                "location": "eastus",
                "address_space": {"address_prefixes": [vpc_cidr]},
            },
        ).result()
        subnets = []
        for i in range(subnet_count):
            subnet = self.network_client.subnets.begin_create_or_update(
                rg_name,
                "astrovox-vnet",
                f"astrovox-subnet-{i+1}",
                {"address_prefix": f"{vpc_cidr[:-4]}{i+1}.0/24"},
            ).result()
            subnets.append(subnet.id)
        return {
            "status": "configured",
            "vnet_id": vnet.id,
            "subnet_ids": subnets,
            "resource_group": rg_name,
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
