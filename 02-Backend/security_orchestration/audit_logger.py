import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional


class AuditLogger:
    def __init__(self, secret: bytes = b"audit-secret") -> None:
        self._secret = secret
        self._chain: List[Dict[str, Any]] = []

    def log(self, category: str, event: str, actor: str, outcome: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        entry = {
            "category": category,
            "event": event,
            "actor": actor,
            "outcome": outcome,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        entry["signature"] = self._sign(entry)
        self._chain.append(entry)
        return entry

    def chain(self) -> List[Dict[str, Any]]:
        return list(self._chain)

    def verify_integrity(self) -> bool:
        for entry in self._chain:
            sig = entry.get("signature", "")
            expected = self._sign({k: v for k, v in entry.items() if k != "signature"})
            if not hmac.compare_digest(sig, expected):
                return False
        return True

    def entries(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if category is None:
            return list(self._chain)
        return [e for e in self._chain if e.get("category") == category]

    def _sign(self, entry: Dict[str, Any]) -> str:
        payload = json.dumps(entry, sort_keys=True).encode()
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
