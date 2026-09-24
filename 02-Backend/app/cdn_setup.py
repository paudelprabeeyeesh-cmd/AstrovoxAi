"""CDN setup and configuration for AstrovoxAI.

Provides static asset configuration, cache headers, and CDN provider setup.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CDNStaticAssetConfig:
    path_pattern: str
    ttl: int
    compress: bool = True
    immutable: bool = False


class CDNSetup:
    """CDN configuration and setup utilities."""

    def __init__(self):
        self.provider = os.getenv("CDN_PROVIDER", "none")
        self.enabled = self.provider != "none"
        self.cdn_base_url = os.getenv("CDN_BASE_URL", "")
        self.static_assets: List[CDNStaticAssetConfig] = [
            CDNStaticAssetConfig(path_pattern="/static/*", ttl=31536000, compress=True, immutable=True),
            CDNStaticAssetConfig(path_pattern="/assets/*", ttl=31536000, compress=True, immutable=True),
            CDNStaticAssetConfig(path_pattern="/images/*", ttl=604800, compress=True, immutable=False),
            CDNStaticAssetConfig(path_pattern="/docs/*", ttl=3600, compress=True, immutable=False),
        ]

    def get_cache_headers(self, path: str) -> Dict[str, str]:
        for asset in self.static_assets:
            if self._match_pattern(path, asset.path_pattern):
                headers = {
                    "Cache-Control": f"public, max-age={asset.ttl}",
                    "CDN-Cache-Control": f"max-age={asset.ttl}",
                }
                if asset.immutable:
                    headers["Cache-Control"] += ", immutable"
                if asset.compress:
                    headers["Accept-Ranges"] = "bytes"
                return headers
        return {"Cache-Control": "no-cache"}

    def _match_pattern(self, path: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    def get_cdn_url(self, path: str) -> str:
        if self.enabled and self.cdn_base_url:
            return f"{self.cdn_base_url.rstrip('/')}/{path.lstrip('/')}"
        return path

    def purge(self, paths: List[str]) -> bool:
        if not self.enabled:
            return False
        try:
            from app.cdn import cdn_service
            return cdn_service.purge_urls(paths)
        except Exception as exc:  # noqa: BLE001
            logger.error("CDN purge failed: %s", exc)
            return False

    def get_static_asset_config(self) -> List[Dict[str, Any]]:
        return [
            {
                "path_pattern": asset.path_pattern,
                "ttl": asset.ttl,
                "compress": asset.compress,
                "immutable": asset.immutable,
            }
            for asset in self.static_assets
        ]


cdn_setup = CDNSetup()
