"""White-label — custom branding, domains, and themes per tenant."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WhiteLabelConfig:
    config_id: str
    tenant_id: str
    app_name: str = ""
    logo_url: str = ""
    primary_color: str = "#000000"
    secondary_color: str = "#ffffff"
    custom_domain: str = ""
    email_from_name: str = ""
    email_from_address: str = ""
    support_email: str = ""
    legal_name: str = ""
    privacy_policy_url: str = ""
    terms_of_service_url: str = ""
    favicon_url: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WhiteLabelManager:
    def __init__(self):
        self._configs: Dict[str, WhiteLabelConfig] = {}

    def set_config(self, tenant_id: str, app_name: str = "", logo_url: str = "", primary_color: str = "#000000", secondary_color: str = "#ffffff", custom_domain: str = "", email_from_name: str = "", email_from_address: str = "", support_email: str = "", legal_name: str = "", privacy_policy_url: str = "", terms_of_service_url: str = "", favicon_url: str = "") -> WhiteLabelConfig:
        existing = next((c for c in self._configs.values() if c.tenant_id == tenant_id), None)
        if existing:
            existing.app_name = app_name or existing.app_name
            existing.logo_url = logo_url or existing.logo_url
            existing.primary_color = primary_color or existing.primary_color
            existing.secondary_color = secondary_color or existing.secondary_color
            existing.custom_domain = custom_domain or existing.custom_domain
            existing.email_from_name = email_from_name or existing.email_from_name
            existing.email_from_address = email_from_address or existing.email_from_address
            existing.support_email = support_email or existing.support_email
            existing.legal_name = legal_name or existing.legal_name
            existing.privacy_policy_url = privacy_policy_url or existing.privacy_policy_url
            existing.terms_of_service_url = terms_of_service_url or existing.terms_of_service_url
            existing.favicon_url = favicon_url or existing.favicon_url
            existing.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info("Updated white-label config for tenant %s", tenant_id)
            return existing
        config_id = str(uuid.uuid4())
        config = WhiteLabelConfig(
            config_id=config_id,
            tenant_id=tenant_id,
            app_name=app_name,
            logo_url=logo_url,
            primary_color=primary_color,
            secondary_color=secondary_color,
            custom_domain=custom_domain,
            email_from_name=email_from_name,
            email_from_address=email_from_address,
            support_email=support_email,
            legal_name=legal_name,
            privacy_policy_url=privacy_policy_url,
            terms_of_service_url=terms_of_service_url,
            favicon_url=favicon_url,
        )
        self._configs[config_id] = config
        logger.info("Created white-label config for tenant %s", tenant_id)
        return config

    def get_config(self, tenant_id: str) -> Optional[WhiteLabelConfig]:
        return next((c for c in self._configs.values() if c.tenant_id == tenant_id), None)

    def get_config_by_domain(self, domain: str) -> Optional[WhiteLabelConfig]:
        for config in self._configs.values():
            if config.custom_domain == domain:
                return config
        return None

    def list_configs(self) -> List[dict]:
        return [
            {
                "config_id": c.config_id,
                "tenant_id": c.tenant_id,
                "app_name": c.app_name,
                "custom_domain": c.custom_domain,
                "primary_color": c.primary_color,
                "updated_at": c.updated_at,
            }
            for c in self._configs.values()
        ]


white_label_manager = WhiteLabelManager()
