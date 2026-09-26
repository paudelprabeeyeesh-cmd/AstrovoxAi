"""Encryption compliance checks."""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class EncryptionCompliance:
    def validate(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings = []
        if config.get("encryption_at_rest") is not True:
            findings.append({"control": "Encryption at Rest", "status": "fail", "message": "Encryption at rest is not enabled"})
        if config.get("tls_version") not in ("TLSv1.2", "TLSv1.3"):
            findings.append({"control": "TLS", "status": "fail", "message": "TLS version is below 1.2"})
        if config.get("key_rotation_days", 0) > 90:
            findings.append({"control": "Key Rotation", "status": "fail", "message": "Key rotation interval exceeds 90 days"})
        if not findings:
            findings.append({"control": "Encryption", "status": "pass", "message": "All encryption controls are satisfied"})
        return findings
