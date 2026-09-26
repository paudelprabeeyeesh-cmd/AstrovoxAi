from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SafetyLayer:
    def __init__(self):
        self.blocklist: List[str] = []
        self.allowlist: List[str] = []
        self.rate_limits: Dict[str, int] = {}

    def validate_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        action_str = str(action)
        for blocked in self.blocklist:
            if blocked in action_str.lower():
                return False, f"Blocked action containing: {blocked}"
        return True, None

    def sanitize_output(self, output: str) -> str:
        for blocked in self.blocklist:
            output = output.replace(blocked, '[REDACTED]')
        return output

    def add_blocklist(self, term: str) -> None:
        self.blocklist.append(term.lower())

    def check_rate_limit(self, key: str, limit: int) -> bool:
        current = self.rate_limits.get(key, 0)
        if current >= limit:
            return False
        self.rate_limits[key] = current + 1
        return True


class ToolGate:
    def __init__(self, safety_layer: SafetyLayer):
        self.safety_layer = safety_layer

    def gate(self, tool_name: str, args: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if tool_name in self.safety_layer.blocklist:
            return False, f"Tool {tool_name} is blocked"
        return True, None
