import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RegionConfig:
    id: str
    code: str
    name: str
    country: str = ""
    data_residency_required: bool = False
    compliance_frameworks: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: float = field(default_factory=datetime.now(timezone.utc).timestamp)


class DataResidencyManager:
    def __init__(self):
        self.regions: Dict[str, RegionConfig] = {}
        self.org_residency: Dict[str, str] = {}

    def register_region(self, code: str, name: str, country: str = "", data_residency_required: bool = False, compliance_frameworks: List[str] = None) -> RegionConfig:
        region_id = str(uuid.uuid4())
        config = RegionConfig(
            id=region_id,
            code=code,
            name=name,
            country=country,
            data_residency_required=data_residency_required,
            compliance_frameworks=compliance_frameworks or [],
        )
        self.regions[code] = config
        logger.info("Registered region %s (%s)", code, name)
        return config

    def get_region(self, code: str) -> Optional[RegionConfig]:
        return self.regions.get(code)

    def list_regions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "country": r.country,
                "data_residency_required": r.data_residency_required,
                "compliance_frameworks": r.compliance_frameworks,
                "is_active": r.is_active,
            }
            for r in self.regions.values()
        ]

    def set_org_residency(self, org_id: str, region_code: str) -> bool:
        if region_code not in self.regions:
            return False
        self.org_residency[org_id] = region_code
        logger.info("Set org %s residency to %s", org_id, region_code)
        return True

    def get_org_residency(self, org_id: str) -> Optional[str]:
        return self.org_residency.get(org_id)

    def validate_data_location(self, org_id: str, data_region: str) -> bool:
        org_region = self.org_residency.get(org_id)
        if not org_region:
            return True
        region_config = self.regions.get(org_region)
        if region_config and region_config.data_residency_required:
            return org_region == data_region
        return True

    def get_compliance_frameworks(self, org_id: str) -> List[str]:
        org_region = self.org_residency.get(org_id)
        if not org_region:
            return []
        region_config = self.regions.get(org_region)
        return region_config.compliance_frameworks if region_config else []


data_residency_manager = DataResidencyManager()

data_residency_manager.register_region("us-east-1", "US East", "US", data_residency_required=True, compliance_frameworks=["SOC2", "HIPAA"])
data_residency_manager.register_region("us-west-2", "US West", "US", data_residency_required=True, compliance_frameworks=["SOC2", "HIPAA"])
data_residency_manager.register_region("eu-west-1", "EU West", "IE", data_residency_required=True, compliance_frameworks=["GDPR", "SOC2"])
data_residency_manager.register_region("eu-central-1", "EU Central", "DE", data_residency_required=True, compliance_frameworks=["GDPR", "BSI"])
data_residency_manager.register_region("ap-southeast-1", "APAC Southeast", "SG", data_residency_required=True, compliance_frameworks=["PDPA", "ISO27001"])
