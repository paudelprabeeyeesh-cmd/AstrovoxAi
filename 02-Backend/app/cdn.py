"""CDN integration for AstrovoxAI backend.

Supports Cloudflare, AWS CloudFront, and custom CDN configurations.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CDNConfig:
    provider: str
    zone_id: Optional[str] = None
    api_token: Optional[str] = None
    distribution_id: Optional[str] = None
    cdn_base_url: Optional[str] = None
    enabled: bool = True

    @classmethod
    def from_env(cls) -> "CDNConfig":
        provider = os.getenv("CDN_PROVIDER", "none")
        return cls(
            provider=provider,
            zone_id=os.getenv("CLOUDFLARE_ZONE_ID"),
            api_token=os.getenv("CLOUDFLARE_API_TOKEN"),
            distribution_id=os.getenv("CLOUDFRONT_DISTRIBUTION_ID"),
            cdn_base_url=os.getenv("CDN_BASE_URL"),
            enabled=provider != "none",
        )


class CDNService:
    """CDN purge and configuration management."""

    def __init__(self, config: Optional[CDNConfig] = None):
        self.config = config or CDNConfig.from_env()
        self._client = self._init_client()

    def _init_client(self) -> Any:
        if not self.config.enabled:
            return None
        try:
            if self.config.provider == "cloudflare":
                import cloudscraper

                return cloudscraper.CloudScraper()
            if self.config.provider == "cloudfront":
                import boto3

                return boto3.client("cloudfront", region_name="us-east-1")
        except Exception as exc:  # noqa: BLE001
            logger.warning("CDN client init failed: %s", exc)
        return None

    def purge_urls(self, urls: list[str]) -> bool:
        if not self.config.enabled or not self._client:
            return False
        try:
            if self.config.provider == "cloudflare":
                import requests

                requests.post(
                    f"https://api.cloudflare.com/client/v4/zones/{self.config.zone_id}/purge_cache",
                    headers={"Authorization": f"Bearer {self.config.api_token}"},
                    json={"files": urls},
                    timeout=10,
                )
                return True
            if self.config.provider == "cloudfront":
                self._client.create_invalidation(
                    DistributionId=self.config.distribution_id,
                    InvalidationBatch={
                        "Paths": {"Quantity": len(urls), "Items": urls},
                        "CallerReference": str(hash(tuple(urls))),
                    },
                )
                return True
        except Exception as exc:  # noqa: BLE001
            logger.error("CDN purge failed: %s", exc)
        return False

    def purge_prefix(self, prefix: str) -> bool:
        if not self.config.enabled or not self._client:
            return False
        try:
            if self.config.provider == "cloudflare":
                import requests

                requests.post(
                    f"https://api.cloudflare.com/client/v4/zones/{self.config.zone_id}/purge_cache",
                    headers={"Authorization": f"Bearer {self.config.api_token}"},
                    json={"prefix": prefix},
                    timeout=10,
                )
                return True
            if self.config.provider == "cloudfront":
                self._client.create_invalidation(
                    DistributionId=self.config.distribution_id,
                    InvalidationBatch={
                        "Paths": {"Quantity": 1, "Items": [f"/*{prefix}*"]},
                        "CallerReference": f"prefix-{hash(prefix)}",
                    },
                )
                return True
        except Exception as exc:  # noqa: BLE001
            logger.error("CDN prefix purge failed: %s", exc)
        return False

    def get_cdn_url(self, path: str) -> str:
        if self.config.cdn_base_url:
            return f"{self.config.cdn_base_url.rstrip('/')}/{path.lstrip('/')}"
        return path


cdn_service = CDNService()
