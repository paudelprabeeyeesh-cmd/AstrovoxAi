import abc
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class CloudProvider(Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class DeploymentTarget(Enum):
    EKS = "eks"
    ECS = "ecs"
    EC2 = "ec2"
    AKS = "aks"
    ACR = "acr"
    GKE = "gke"
    GCR = "gcr"
    CLOUD_RUN = "cloud_run"
    VM = "vm"


@dataclass
class StorageCredentials:
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    session_token: Optional[str] = None
    endpoint: Optional[str] = None
    region: Optional[str] = None
    account_name: Optional[str] = None
    account_key: Optional[str] = None
    project_id: Optional[str] = None


@dataclass
class ContainerRegistryConfig:
    registry_url: str
    repository_name: str
    tag: str = "latest"
    auth_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class KubernetesConfig:
    cluster_name: str
    namespace: str = "default"
    context: Optional[str] = None
    kubeconfig_path: Optional[str] = None


@dataclass
class DeploymentConfig:
    provider: CloudProvider
    target: DeploymentTarget
    container_registry: Optional[ContainerRegistryConfig] = None
    kubernetes: Optional[KubernetesConfig] = None
    storage_credentials: Optional[StorageCredentials] = None
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None


class BaseCloudAdapter(abc.ABC):
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.provider = config.provider

    @abc.abstractmethod
    def deploy_container(self, image_uri: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def provision_storage(self, bucket_name: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def setup_iam_roles(self, role_name: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def configure_networking(self, vpc_cidr: str, subnet_count: int = 3) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def setup_dns(self, domain_name: str, records: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def provision_gpu_instance(self, instance_type: str, count: int = 1) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def deploy_edge_function(self, function_name: str, runtime: str, code_uri: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def invalidate_cdn_cache(self, distribution_id: str, paths: list) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def setup_multi_region(self, regions: list, primary_region: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def configure_load_balancer(self, lb_name: str, listeners: list) -> Dict[str, Any]:
        raise NotImplementedError
