from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from ..deployment.base_adapter import BaseCloudAdapter


@dataclass
class SubnetConfig:
    cidr: str
    availability_zone: str
    public: bool = False
    map_public_ip: bool = False


@dataclass
class VPCConfig:
    cidr: str
    name: str
    subnets: List[SubnetConfig]
    enable_dns_hostnames: bool = True
    enable_dns_support: bool = True


class VPCManager:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.vpcs: Dict[str, VPCConfig] = {}

    def create_vpc(self, config: VPCConfig) -> Dict[str, Any]:
        self.vpcs[config.name] = config
        return self.adapter.configure_networking(config.cidr, len(config.subnets))

    def provision_subnets(self, vpc_id: str, subnet_configs: List[SubnetConfig]) -> Dict[str, Any]:
        subnet_ids = []
        for subnet_config in subnet_configs:
            subnet_ids.append(subnet_config.cidr)
        return {
            "vpc_id": vpc_id,
            "subnet_ids": subnet_ids,
            "status": "provisioned",
        }

    def create_internet_gateway(self, vpc_id: str, name: str) -> Dict[str, Any]:
        return {
            "status": "created",
            "vpc_id": vpc_id,
            "name": name,
        }

    def create_nat_gateway(self, subnet_id: str, name: str) -> Dict[str, Any]:
        return {
            "status": "created",
            "subnet_id": subnet_id,
            "name": name,
        }

    def create_route_table(
        self,
        vpc_id: str,
        name: str,
        destination_cidr: str = "0.0.0.0/0",
        gateway_id: Optional[str] = None,
        nat_gateway_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        routes = [{"destination_cidr_block": destination_cidr}]
        if gateway_id:
            routes[0]["gateway_id"] = gateway_id
        if nat_gateway_id:
            routes[0]["nat_gateway_id"] = nat_gateway_id
        return {
            "status": "created",
            "vpc_id": vpc_id,
            "name": name,
            "routes": routes,
        }

    def associate_route_table(self, route_table_id: str, subnet_id: str) -> Dict[str, Any]:
        return {
            "status": "associated",
            "route_table_id": route_table_id,
            "subnet_id": subnet_id,
        }

    def create_security_group(
        self,
        vpc_id: str,
        name: str,
        ingress_rules: List[Dict[str, Any]],
        egress_rules: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "status": "created",
            "vpc_id": vpc_id,
            "name": name,
            "ingress_rules": ingress_rules,
            "egress_rules": egress_rules,
        }
