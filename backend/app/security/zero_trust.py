"""Zero Trust continuous verification and identity-aware access control."""
import hashlib
import logging
import time
import secrets
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class TrustLevel(Enum):
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


@dataclass
class TrustContext:
    subject_id: str
    trust_score: float = 0.0
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    verified_at: float = field(default_factory=time.time)
    factors: Dict[str, Any] = field(default_factory=dict)
    risk_indicators: List[str] = field(default_factory=list)


class ZeroTrustEngine:
    def __init__(self):
        self._contexts: Dict[str, TrustContext] = {}
        self._verification_requirements: Dict[str, Dict[str, float]] = {
            "default": {"identity": 0.2, "device": 0.2, "behavior": 0.2, "network": 0.2, "entitlement": 0.2},
        }
        self._lock = __import__('threading').Lock()
        self._session_ttl = 1800

    def evaluate_trust(self, subject_id: str, factors: Dict[str, Any]) -> TrustContext:
        scores = {
            "identity": self._score_identity(factors.get("identity", {})),
            "device": self._score_device(factors.get("device", {})),
            "behavior": self._score_behavior(factors.get("behavior", {})),
            "network": self._score_network(factors.get("network", {})),
            "entitlement": self._score_entitlement(factors.get("entitlement", {})),
        }
        requirements = self._verification_requirements.get(subject_id, self._verification_requirements["default"])
        total = sum(scores.get(k, 0.0) * v for k, v in requirements.items())
        level = TrustLevel.UNTRUSTED
        if total >= 0.9:
            level = TrustLevel.VERIFIED
        elif total >= 0.7:
            level = TrustLevel.HIGH
        elif total >= 0.5:
            level = TrustLevel.MEDIUM
        elif total >= 0.3:
            level = TrustLevel.LOW

        with self._lock:
            ctx = TrustContext(subject_id=subject_id, trust_score=total, trust_level=level, factors=scores, risk_indicators=self._detect_risks(factors))
            self._contexts[subject_id] = ctx
            return ctx

    def is_authorized(self, subject_id: str, action: str, min_level: TrustLevel = TrustLevel.MEDIUM) -> bool:
        with self._lock:
            ctx = self._contexts.get(subject_id)
        if not ctx:
            return False
        if time.time() - ctx.verified_at > self._session_ttl:
            return False
        return ctx.trust_level.value in (min_level.value, TrustLevel.VERIFIED.value) or ctx.trust_level.value > min_level.value

    def _score_identity(self, data: Dict[str, Any]) -> float:
        if not data:
            return 0.1
        score = 0.4
        if data.get("mfa_verified"):
            score += 0.3
        if data.get("identity_provider") in ("sso", "saml", "oauth"):
            score += 0.2
        if data.get("credential_age", 9999) < 86400:
            score += 0.1
        return min(1.0, score)

    def _score_device(self, data: Dict[str, Any]) -> float:
        if not data:
            return 0.1
        score = 0.3
        if data.get("managed"):
            score += 0.3
        if data.get("disk_encrypted"):
            score += 0.2
        if data.get("os_patched"):
            score += 0.1
        if not data.get("jailbroken") and not data.get("rooted"):
            score += 0.1
        return min(1.0, score)

    def _score_behavior(self, data: Dict[str, Any]) -> float:
        if not data:
            return 0.2
        score = 0.4
        if data.get("baseline_match", 0) > 0.8:
            score += 0.3
        if data.get("anomaly_score", 1.0) < 0.2:
            score += 0.2
        return min(1.0, score)

    def _score_network(self, data: Dict[str, Any]) -> float:
        if not data:
            return 0.2
        score = 0.4
        if data.get("private_ip"):
            score += 0.2
        if not data.get("proxy_detected") and not data.get("vpn_detected"):
            score += 0.2
        if data.get("geo_consistent"):
            score += 0.1
        return min(1.0, score)

    def _score_entitlement(self, data: Dict[str, Any]) -> float:
        if not data:
            return 0.2
        score = 0.5
        if data.get("least_privilege"):
            score += 0.3
        if data.get("policy_compliant"):
            score += 0.2
        return min(1.0, score)

    def _detect_risks(self, factors: Dict[str, Any]) -> List[str]:
        risks = []
        identity = factors.get("identity", {})
        if identity.get("password_only"):
            risks.append("weak_identity")
        device = factors.get("device", {})
        if device.get("jailbroken") or device.get("rooted"):
            risks.append("compromised_device")
        network = factors.get("network", {})
        if network.get("proxy_detected"):
            risks.append("anonymous_network")
        return risks

    def refresh(self, subject_id: str):
        with self._lock:
            ctx = self._contexts.get(subject_id)
            if ctx:
                ctx.verified_at = time.time()


zero_trust_engine = ZeroTrustEngine()
