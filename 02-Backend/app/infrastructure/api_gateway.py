"""API Gateway client for Kong."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from app.core.config import get_config

logger = logging.getLogger(__name__)


class APIGatewayClient:
    """Kong API Gateway client."""

    def __init__(self) -> None:
        self._config = get_config()
        self._base_url = self._config.api_gateway.url
        self._admin_url = f"{self._base_url}/admin"
        self._session = requests.Session()
        if self._config.api_gateway.api_key:
            self._session.headers.update({"apikey": self._config.api_gateway.api_key})

    def create_route(self, service: str, paths: list, methods: Optional[list] = None) -> Dict[str, Any]:
        data = {
            "service": service,
            "paths": paths,
            "methods": methods or ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        }
        response = self._session.post(f"{self._admin_url}/routes", json=data)
        response.raise_for_status()
        return response.json()

    def create_service(self, name: str, url: str) -> Dict[str, Any]:
        data = {"name": name, "url": url}
        response = self._session.post(f"{self._admin_url}/services", json=data)
        response.raise_for_status()
        return response.json()

    def add_plugin(self, plugin_name: str, config: Dict[str, Any], service: Optional[str] = None, route: Optional[str] = None) -> Dict[str, Any]:
        data = {
            "name": plugin_name,
            "config": config,
        }
        if service:
            data["service"] = service
        if route:
            data["route"] = route
        response = self._session.post(f"{self._admin_url}/plugins", json=data)
        response.raise_for_status()
        return response.json()

    def list_routes(self, service: Optional[str] = None) -> list:
        params = {}
        if service:
            params["service"] = service
        response = self._session.get(f"{self._admin_url}/routes", params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def delete_route(self, route_id: str) -> None:
        response = self._session.delete(f"{self._admin_url}/routes/{route_id}")
        response.raise_for_status()


_gateway: Optional[APIGatewayClient] = None


def get_api_gateway() -> APIGatewayClient:
    global _gateway
    if _gateway is None:
        _gateway = APIGatewayClient()
    return _gateway
