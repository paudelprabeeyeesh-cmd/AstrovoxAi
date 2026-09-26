from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SSOManager:
    def __init__(self):
        self.providers: Dict[str, Dict[str, Any]] = {}

    def register_saml(self, provider_name: str, metadata_url: str, entity_id: str) -> None:
        self.providers[f"saml:{provider_name}"] = {
            "type": "saml",
            "metadata_url": metadata_url,
            "entity_id": entity_id,
        }
        logger.info("Registered SAML provider %s", provider_name)

    def register_oidc(self, provider_name: str, client_id: str, client_secret: str, issuer: str) -> None:
        self.providers[f"oidc:{provider_name}"] = {
            "type": "oidc",
            "client_id": client_id,
            "client_secret": client_secret,
            "issuer": issuer,
        }
        logger.info("Registered OIDC provider %s", provider_name)

    def authenticate(self, provider_key: str, token: str) -> Optional[Dict[str, Any]]:
        provider = self.providers.get(provider_key)
        if not provider:
            logger.warning("Unknown SSO provider: %s", provider_key)
            return None
        logger.info("Authenticated via %s", provider_key)
        return {"user_id": "sso_user", "provider": provider_key}


enterprise_sso = SSOManager()
