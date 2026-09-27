"""
API portal for AstrovoxAI.
Main portal service integrating developer registration, API keys, and documentation.
"""

import logging
from typing import Any, Dict, List, Optional

from .developer_registration import DeveloperRegistry
from .api_key_manager import APIKeyManager, APIKeyScope

logger = logging.getLogger(__name__)


class APIPortal:
    """Main API portal service."""

    def __init__(self):
        self.developer_registry = DeveloperRegistry()
        self.api_key_manager = APIKeyManager()

    def register_developer(
        self,
        email: str,
        name: str,
        password: str,
        company: Optional[str] = None,
    ) -> Dict[str, Any]:
        developer = self.developer_registry.register(email, name, password, company)
        key, raw_key = self.api_key_manager.create_key(
            developer_id=developer.developer_id,
            name="Default Key",
            scopes=[APIKeyScope.INFERENCE],
            expires_in_days=90,
        )
        logger.info("Developer registered via portal: %s", developer.developer_id)
        return {
            "developer": developer.to_dict(),
            "api_key": {
                "key_id": key.key_id,
                "prefix": key.prefix,
                "scopes": [s.value for s in key.scopes],
                "secret": raw_key,
            },
        }

    def get_api_keys(self, developer_id: str) -> List[Dict[str, Any]]:
        keys = self.api_key_manager.list_keys(developer_id)
        return [k.to_dict() for k in keys]

    def create_api_key(
        self,
        developer_id: str,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        key_scopes = [APIKeyScope(s) for s in scopes] if scopes else None
        key, raw_key = self.api_key_manager.create_key(
            developer_id=developer_id,
            name=name,
            scopes=key_scopes,
            expires_in_days=expires_in_days,
        )
        return {
            "key_id": key.key_id,
            "name": key.name,
            "prefix": key.prefix,
            "scopes": [s.value for s in key.scopes],
            "secret": raw_key,
        }

    def revoke_api_key(self, developer_id: str, key_id: str) -> None:
        key = self.api_key_manager.get_key(key_id)
        if not key or key.developer_id != developer_id:
            raise ValueError("API key not found")
        self.api_key_manager.revoke_key(key_id)
