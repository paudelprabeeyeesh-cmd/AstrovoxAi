"""CDN client for Cloudflare."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from app.core.config import get_config

logger = logging.getLogger(__name__)


class CDNClient:
    """Cloudflare CDN client."""

    def __init__(self) -> None:
        self._config = get_config()
        self._zone_id = self._config.cdn.zone_id
        self._api_token = self._config.cdn.api_token
        self._base_url = f"https://api.cloudflare.com/client/v4/zones/{self._zone_id}"
        self._session = requests.Session()
        if self._api_token:
            self._session.headers.update({
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
            })

    def purge_cache(self, files: Optional[list] = None) -> Dict[str, Any]:
        data = {"purge_everything": True}
        if files:
            data = {"files": files}
        response = self._session.post(f"{self._base_url}/purge_cache", json=data)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Cache purge result: {result}")
        return result

    def create_page_rule(self, url_pattern: str, actions: list) -> Dict[str, Any]:
        data = {
            "targets": [{"target": "url", "constraint": {"operator": "matches", "value": url_pattern}}],
            "actions": actions,
            "priority": 1,
            "status": "active",
        }
        response = self._session.post(f"{self._base_url}/pagerules", json=data)
        response.raise_for_status()
        return response.json()

    def update_dns_record(self, zone_id: str, record_id: str, content: str, ttl: int = 1) -> Dict[str, Any]:
        response = self._session.put(
            f"{self._base_url}/dns_records/{record_id}",
            json={"type": "A", "name": "astrovox.ai", "content": content, "ttl": ttl},
        )
        response.raise_for_status()
        return response.json()

    def get_analytics(self, since: Optional[str] = None, until: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        response = self._session.get(f"{self._base_url}/analytics/dashboard", params=params)
        response.raise_for_status()
        return response.json()


_cdn: Optional[CDNClient] = None


def get_cdn() -> CDNClient:
    global _cdn
    if _cdn is None:
        _cdn = CDNClient()
    return _cdn
