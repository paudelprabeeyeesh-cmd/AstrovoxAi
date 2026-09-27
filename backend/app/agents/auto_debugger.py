from typing import Any, Dict, List, Optional
import logging
import time
import hashlib

logger = logging.getLogger(__name__)


class AutoDebugger:
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.error_history: List[Dict[str, Any]] = []
        self.error_patterns: Dict[str, Dict[str, Any]] = {}
        self.fix_registry: Dict[str, List[str]] = {}

    def _fingerprint(self, error: Exception, context: Dict[str, Any]) -> str:
        raw = f"{type(error).__name__}:{str(error)}:{sorted(context.items())}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def diagnose(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        fp = self._fingerprint(error, context)
        diagnosis = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "root_cause": self._infer_root_cause(error),
            "fingerprint": fp,
            "timestamp": time.time(),
        }
        self.error_history.append(diagnosis)
        pattern = self.error_patterns.get(fp, {"count": 0, "first_seen": time.time(), "solutions": []})
        pattern["count"] += 1
        pattern["last_seen"] = time.time()
        self.error_patterns[fp] = pattern
        return diagnosis

    def _infer_root_cause(self, error: Exception) -> str:
        msg = str(error).lower()
        if "timeout" in msg:
            return "timeout"
        if "connection" in msg:
            return "connection_error"
        if "null" in msg or "none" in msg:
            return "null_reference"
        if "permission" in msg or "auth" in msg:
            return "permission_error"
        if "memory" in msg or "oom" in msg:
            return "memory_error"
        if "syntax" in msg or "invalid" in msg:
            return "syntax_error"
        return "unknown"

    def repair(self, diagnosis: Dict[str, Any]) -> Optional[str]:
        root_cause = diagnosis.get("root_cause")
        repairs = {
            "timeout": "Retry with exponential backoff and increased timeout.",
            "connection_error": "Check network connectivity and retry with circuit breaker.",
            "null_reference": "Add null guard and validate inputs before access.",
            "permission_error": "Verify credentials, scopes, and permissions.",
            "memory_error": "Reduce batch size or free unused resources before retry.",
            "syntax_error": "Validate input schema and sanitize payload.",
            "unknown": "Escalate to human review with full context.",
        }
        repair = repairs.get(root_cause)
        if repair:
            fp = diagnosis.get("fingerprint")
            if fp:
                self.fix_registry.setdefault(fp, []).append(repair)
        return repair

    def attempt_fix(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        diagnosis = self.diagnose(error, context)
        repair = self.repair(diagnosis)
        return {
            "diagnosis": diagnosis,
            "repair": repair,
            "retry": repair is not None,
            "backoff": self.backoff_factor ** self._retry_count(diagnosis),
        }

    def _retry_count(self, diagnosis: Dict[str, Any]) -> int:
        fp = diagnosis.get("fingerprint", "")
        return sum(1 for d in self.error_history if d.get("fingerprint") == fp)

    def self_reflect(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        reflection = {
            "success": outcome.get("status") == "success",
            "issues": [h for h in self.error_history if h.get("root_cause") not in (None, "resolved")],
            "improvement": "Adjust retry policy and add preconditions.",
            "repeated_errors": self._detect_repeated_errors(),
        }
        return reflection

    def _detect_repeated_errors(self) -> List[Dict[str, Any]]:
        repeated = []
        for fp, pattern in self.error_patterns.items():
            if pattern.get("count", 0) > 1:
                repeated.append({"fingerprint": fp, "count": pattern["count"], "solutions": pattern.get("solutions", [])[:3]})
        return repeated

    def validate_fix(self, diagnosis: Dict[str, Any], outcome: Dict[str, Any]) -> bool:
        if outcome.get("status") == "success":
            fp = diagnosis.get("fingerprint")
            if fp:
                pattern = self.error_patterns.get(fp)
                if pattern is not None:
                    pattern["solutions"] = list({*pattern.get("solutions", []), diagnosis.get("repair", "")})
            return True
        return False

    def get_repair_stats(self) -> Dict[str, Any]:
        total = len(self.error_history)
        by_cause: Dict[str, int] = {}
        for entry in self.error_history:
            cause = entry.get("root_cause", "unknown")
            by_cause[cause] = by_cause.get(cause, 0) + 1
        return {"total_errors": total, "by_root_cause": by_cause, "repeated_patterns": len(self.error_patterns)}
