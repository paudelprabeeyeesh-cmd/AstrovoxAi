from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AutoDebugger:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.error_history: List[Dict[str, Any]] = []

    def diagnose(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        diagnosis = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "root_cause": self._infer_root_cause(error),
        }
        self.error_history.append(diagnosis)
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
        return "unknown"

    def repair(self, diagnosis: Dict[str, Any]) -> Optional[str]:
        root_cause = diagnosis.get("root_cause")
        repairs = {
            "timeout": "Retry with exponential backoff and increased timeout.",
            "connection_error": "Check network connectivity and retry.",
            "null_reference": "Add null guard and validate inputs.",
            "permission_error": "Verify credentials and permissions.",
            "unknown": "Escalate to human review.",
        }
        return repairs.get(root_cause)

    def self_reflect(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        reflection = {
            "success": outcome.get("status") == "success",
            "issues": [h for h in self.error_history if h.get("root_cause") != "resolved"],
            "improvement": "Adjust retry policy and add preconditions.",
        }
        return reflection
