from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..deployment.base_adapter import BaseCloudAdapter


class DNSRecordType(Enum):
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    NS = "NS"
    PTR = "PTR"
    SRV = "SRV"


class DNSRoutingPolicy(Enum):
    SIMPLE = "simple"
    WEIGHTED = "weighted"
    LATENCY = "latency"
    FAILOVER = "failover"
    GEO_LOCATION = "geo_location"


@dataclass
class DNSRecord:
    name: str
    record_type: DNSRecordType
    values: List[str]
    ttl: int = 300
    routing_policy: DNSRoutingPolicy = DNSRoutingPolicy.SIMPLE
    weight: Optional[int] = None
    region: Optional[str] = None
    health_check_id: Optional[str] = None


class DNSManager:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.zones: Dict[str, Dict[str, Any]] = {}

    def create_zone(self, domain_name: str) -> Dict[str, Any]:
        zone = self.adapter.setup_dns(domain_name, {})
        self.zones[domain_name] = zone
        return zone

    def create_record(self, zone_id: str, record: DNSRecord) -> Dict[str, Any]:
        record_data = {
            "Name": record.name,
            "Type": record.record_type.value,
            "TTL": record.ttl,
            "ResourceRecords": [{"Value": value} for value in record.values],
        }
        return {
            "status": "created",
            "zone_id": zone_id,
            "record": record_data,
        }

    def setup_failover(
        self,
        zone_id: str,
        primary_record: DNSRecord,
        secondary_record: DNSRecord,
        health_check_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "status": "configured",
            "zone_id": zone_id,
            "primary": primary_record.name,
            "secondary": secondary_record.name,
            "health_check": health_check_config,
        }

    def setup_geo_routing(
        self,
        zone_id: str,
        records: List[tuple],
    ) -> Dict[str, Any]:
        return {
            "status": "configured",
            "zone_id": zone_id,
            "records": [{"name": r[0].name, "region": r[1]} for r in records],
        }

    def setup_weighted_routing(
        self,
        zone_id: str,
        records: List[tuple],
    ) -> Dict[str, Any]:
        return {
            "status": "configured",
            "zone_id": zone_id,
            "records": [{"name": r[0].name, "weight": r[1]} for r in records],
        }
