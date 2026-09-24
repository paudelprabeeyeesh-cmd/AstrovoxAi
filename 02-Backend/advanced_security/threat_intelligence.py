import hashlib
import hmac
import json
import os
import random
import re
from typing import Any, Dict, List, Optional, Tuple


class TLP:
    WHITE = "white"
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class ThreatIntelligence:
    def __init__(self, secret: Optional[str] = None) -> None:
        self._secret = (secret or "threat-intel").encode()
        self._iocs: List[Dict[str, Any]] = []
        self._ttps: Dict[str, Any] = {}

    def add_ioc(self, value: str, ioc_type: str, tlp: str = TLP.GREEN) -> None:
        self._iocs.append({"value": value, "type": ioc_type, "tlp": tlp})

    def analyze_file(self, hashes: Dict[str, str]) -> Dict[str, Any]:
        malware = any(h in self._hash_reputation for h in hashes.values())
        return {"malicious": malware, "hashes": hashes, "reasons": ["reputation"] if malware else []}

    def analyze_ip(self, ip: str) -> Dict[str, Any]:
        if ":" in ip:
            return self._analyze_ipv6(ip)
        return self._analyze_ipv4(ip)

    def _analyze_ipv4(self, ip: str) -> Dict[str, Any]:
        malicious = ip in self._reputation
        return {"ip": ip, "malicious": malicious, "confidence": 0.9 if malicious else 0.3, "reasons": ["reputation"] if malicious else []}

    def _analyze_ipv6(self, ip: str) -> Dict[str, Any]:
        return {"ip": ip, "malicious": False, "confidence": 0.1, "reasons": ["no_ipv6_data"]}

    def extract_iocs(self, text: str) -> Dict[str, List[str]]:
        return {"ips": self._extract_ips(text), "domains": self._extract_domains(text), "hashes": self._extract_hashes(text), "urls": self._extract_urls(text)}

    def match_iocs(self, text: str) -> List[Dict[str, Any]]:
        extracted = self.extract_iocs(text)
        matched = []
        for ioc in self._iocs:
            for k, vals in extracted.items():
                if ioc["value"] in vals:
                    matched.append({**ioc, "category": k})
        return matched

    def _extract_ips(self, text: str) -> List[str]:
        return self._findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)

    def _extract_domains(self, text: str) -> List[str]:
        return self._findall(r'[a-z0-9.-]+\.[a-z]{2,}', text, re.IGNORECASE)

    def _extract_hashes(self, text: str) -> List[str]:
        return self._findall(r'[A-Fa-f0-9]{32,}', text)

    def _extract_urls(self, text: str) -> List[str]:
        return self._findall(r'https?://[^\s,]+', text)

    def _findall(self, pattern: str, text: str, flags: int = 0) -> List[str]:
        import re
        return re.findall(pattern, text, flags)

    def enrich_ip(self, ip: str) -> Dict[str, Any]:
        return {"ip": ip, "geo": "unknown", "asn": "unknown", "tags": []}

    def enrich_domain(self, domain: str) -> Dict[str, Any]:
        return {"domain": domain, "tags": [], "nameservers": [], "registrar": "unknown"}

    def reputation(self, ioc: str, ioc_type: str) -> float:
        return random.random()

    def yara_match(self, rules: Dict[str, Any], data: bytes) -> List[Dict[str, Any]]:
        return []

    def stix_report(self, iocs: List[Dict[str, Any]]) -> str:
        return json.dumps({"type": "report", "objects": iocs})

    def ioc_vault(self, limit: int = 1000) -> List[Dict[str, Any]]:
        return self._iocs[:limit]

    def mitre_technique(self, technique_id: str) -> Dict[str, Any]:
        return {"id": technique_id, "name": "Unknown", "tactics": [], "description": "", "references": []}

    def _sign(self, payload: bytes) -> str:
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()

    @property
    def _hash_reputation(self) -> Dict[str, str]:
        return {"f0e4c2f7": "suspicious", "5d41402a": "clean"}

    @property
    def _reputation(self) -> Dict[str, str]:
        return {"198.51.100.1": "suspicious", "192.0.2.1": "clean"}
