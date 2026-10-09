import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Identity:
    subject: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    trust_rank: int = 0


@dataclass
class VerificationResult:
    success: bool
    risk_score: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    verified_at: float = field(default_factory=time.time)


class ZeroTrustAuthenticator:
    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()
        self._nonces: List[str] = []

    def _nonce(self) -> str:
        return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:16]

    def _sign(self, payload: bytes) -> str:
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()

    def challenge(self, subject: str) -> Dict[str, Any]:
        nonce = self._nonce()
        payload = json.dumps({"subject": subject, "nonce": nonce}).encode()
        return {
            "challenge_id": str(uuid.uuid4()),
            "nonce": nonce,
            "signature": self._sign(payload),
            "expires_at": time.time() + 120,
        }

    def verify(self, subject: str, nonce: str, signature: str) -> VerificationResult:
        if nonce in self._nonces:
            return VerificationResult(success=False, risk_score=1.0, evidence={"reason": "replay"})
        payload = json.dumps({"subject": subject, "nonce": nonce}).encode()
        expected = self._sign(payload)
        if not hmac.compare_digest(expected, signature):
            return VerificationResult(success=False, risk_score=0.9, evidence={"reason": "signature"})
        self._nonces.append(nonce)
        return VerificationResult(success=True, risk_score=0.0, evidence={"subject": subject})


class PolicyEngine:
    def __init__(self) -> None:
        self._rules: List[Dict[str, Any]] = []

    def add_rule(self, effect: str, actions: List[str], resource_attr: str, value: Any) -> None:
        self._rules.append({"effect": effect, "actions": actions, "resource_attr": resource_attr, "value": value})

    def evaluate(self, subject: Identity, action: str, resource: Dict[str, Any]) -> VerificationResult:
        for rule in self._rules:
            if action not in rule["actions"]:
                continue
            if resource.get(rule["resource_attr"]) == rule["value"]:
                return VerificationResult(success=rule["effect"] == "allow", risk_score=0.0 if rule["effect"] == "allow" else 0.8, evidence={"rule": rule})
        return VerificationResult(success=False, risk_score=0.6, evidence={"reason": "implicit_deny"})
