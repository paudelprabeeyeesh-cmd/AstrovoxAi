import json
import time
import logging
import secrets
import base64
import zlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from urllib.parse import urlencode, quote

import requests
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class SAMLBinding(Enum):
    HTTP_POST = "http-post"
    HTTP_REDIRECT = "http-redirect"


@dataclass
class SAMLConfig:
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: Optional[str]
    idp_cert: str
    sp_entity_id: str
    sp_acs_url: str
    sp_slo_url: Optional[str]
    name_id_format: str = "urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress"


class SSOSAMLAdapter:
    def __init__(self, config: SAMLConfig):
        self.config = config
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def build_authn_request(self, binding: SAMLBinding = SAMLBinding.HTTP_REDIRECT) -> Dict[str, Any]:
        request_id = secrets.token_hex(16)
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<saml2p:AuthnRequest xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol"
    ID="{request_id}" Version="2.0" IssueInstant="{timestamp}"
    Destination="{self.config.idp_sso_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    AssertionConsumerServiceURL="{self.config.sp_acs_url}">
  <saml2:Issuer xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion">{self.config.sp_entity_id}</saml2:Issuer>
  <saml2p:NameIDPolicy Format="{self.config.name_id_format}" AllowCreate="true"/>
  <saml2p:RequestedAuthnContext Comparison="exact">
    <saml2:AuthnContextClassRef xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion">urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml2:AuthnContextClassRef>
  </saml2p:RequestedAuthnContext>
</saml2p:AuthnRequest>"""
        if binding == SAMLBinding.HTTP_REDIRECT:
            encoded = base64.urlsafe_b64encode(authn_request.encode('utf-8')).decode('utf-8')
            params = urlencode({"SAMLRequest": encoded})
            return {"url": f"{self.config.idp_sso_url}?{params}", "method": "redirect"}
        else:
            encoded = base64.b64encode(authn_request.encode('utf-8')).decode('utf-8')
            return {"url": self.config.idp_sso_url, "method": "post", "saml_request": encoded}

    def process_saml_response(self, saml_response: str, session_expiry_seconds: int = 3600) -> Dict[str, Any]:
        decoded = base64.b64decode(saml_response).decode('utf-8')
        root = ET.fromstring(decoded)
        ns = {"saml2": "urn:oasis:names:tc:SAML:2.0:assertion", "saml2p": "urn:oasis:names:tc:SAML:2.0:protocol"}
        assertion = root.find(".//saml2:Assertion", ns)
        if assertion is None:
            raise ValueError("No assertion found in SAML response")
        subject = assertion.find("saml2:Subject/saml2:NameID", ns)
        email = subject.text if subject is not None else ""
        attributes = {}
        for attr in assertion.findall(".//saml2:Attribute", ns):
            name = attr.get("Name", "")
            values = [val.text for val in attr.findall("saml2:AttributeValue", ns) if val.text]
            attributes[name] = values[0] if len(values) == 1 else values
        session_id = secrets.token_hex(24)
        self._sessions[session_id] = {
            "email": email,
            "attributes": attributes,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=session_expiry_seconds)).isoformat()
        }
        logger.info(f"SAML login successful for {email}")
        return {"session_id": session_id, "email": email, "attributes": attributes}

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.utcnow() > expires_at:
            del self._sessions[session_id]
            return None
        return session

    def logout(self, session_id: str) -> Optional[str]:
        session = self._sessions.pop(session_id, None)
        if session and self.config.idp_slo_url:
            logout_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<saml2p:LogoutRequest xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol"
    ID="{secrets.token_hex(16)}" Version="2.0" IssueInstant="{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}">
  <saml2:Issuer xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion">{self.config.sp_entity_id}</saml2:Issuer>
  <saml2:NameID xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion" Format="{self.config.name_id_format}">{session['email']}</saml2:NameID>
</saml2p:LogoutRequest>"""
            encoded = base64.b64encode(logout_request.encode('utf-8')).decode('utf-8')
            return f"{self.config.idp_slo_url}?{urlencode({'SAMLRequest': encoded})}"
        return None
