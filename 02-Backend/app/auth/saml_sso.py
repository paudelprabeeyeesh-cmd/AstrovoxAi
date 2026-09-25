"""SAML SSO integration."""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import base64
from xml.etree import ElementTree as ET


@dataclass
class SAMLConfig:
    entity_id: str
    sso_url: str
    slo_url: str
    x509_cert: str
    private_key: str
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"


class SAMLSSO:
    _configs: Dict[str, SAMLConfig] = {}

    @classmethod
    def register(cls, name: str, config: SAMLConfig) -> None:
        cls._configs[name] = config

    @classmethod
    def get(cls, name: str) -> Optional[SAMLConfig]:
        return cls._configs.get(name)

    @classmethod
    def build_auth_request(cls, name: str, audience: str) -> str:
        config = cls.get(name)
        if not config:
            raise ValueError(f"SAML config not found: {name}")
        authn_request = f"""<?xml version="1.0"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    ID="_001" Version="2.0" IssueInstant="{datetime.utcnow().isoformat()}Z"
    Destination="{config.sso_url}" ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    AssertionConsumerServiceURL="{audience}">
    <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">{config.entity_id}</saml:Issuer>
</samlp:AuthnRequest>"""
        return base64.b64encode(authn_request.encode()).decode()

    @classmethod
    def parse_response(cls, saml_response: str) -> Dict[str, Any]:
        try:
            decoded = base64.b64decode(saml_response)
            root = ET.fromstring(decoded)
            return {
                "name_id": root.findtext(".//{urn:oasis:names:tc:SAML:2.0:assertion}NameID", ""),
                "session_index": root.findtext(".//{urn:oasis:names:tc:SAML:2.0:assertion}AuthnStatement/@SessionIndex", ""),
            }
        except Exception as e:
            return {"error": str(e)}
