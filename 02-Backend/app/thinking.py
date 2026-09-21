import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ThinkingConfig:
    def __init__(
        self,
        enabled: bool = False,
        effort: str = "medium",
        max_tokens: Optional[int] = None,
        budget_tokens: Optional[int] = None,
    ):
        self.enabled = enabled
        self.effort = effort
        self.max_tokens = max_tokens
        self.budget_tokens = budget_tokens

    def to_anthropic_params(self) -> dict:
        if not self.enabled:
            return {}
        params = {"type": "enabled"}
        if self.effort == "low":
            params["budget_tokens"] = self.budget_tokens or 1024
        elif self.effort == "medium":
            params["budget_tokens"] = self.budget_tokens or 4096
        elif self.effort == "high":
            params["budget_tokens"] = self.budget_tokens or 16384
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        return params

    def to_openai_params(self) -> dict:
        if not self.enabled:
            return {}
        effort_map = {"low": "low", "medium": "medium", "high": "high"}
        return {"reasoning_effort": effort_map.get(self.effort, "medium")}


def get_thinking_config(effort: str = "medium", enabled: bool = True) -> ThinkingConfig:
    return ThinkingConfig(enabled=enabled, effort=effort)
