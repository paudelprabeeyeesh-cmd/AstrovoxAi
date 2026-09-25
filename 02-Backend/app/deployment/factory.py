from typing import Optional
from .base_adapter import BaseCloudAdapter, DeploymentConfig, CloudProvider
from .aws_adapter import AWSAdapter
from .azure_adapter import AzureAdapter
from .gcp_adapter import GCPAdapter


class CloudAdapterFactory:
    @staticmethod
    def create(config: DeploymentConfig) -> BaseCloudAdapter:
        provider = config.provider
        if provider == CloudProvider.AWS:
            return AWSAdapter(config)
        elif provider == CloudProvider.AZURE:
            return AzureAdapter(config)
        elif provider == CloudProvider.GCP:
            return GCPAdapter(config)
        else:
            raise ValueError(f"Unsupported cloud provider: {provider}")
