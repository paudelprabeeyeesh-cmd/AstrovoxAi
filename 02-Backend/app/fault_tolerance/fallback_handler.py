import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class FallbackHandler:
    def __init__(self, primary: Callable[..., Any], fallback: Callable[..., Any]):
        self.primary = primary
        self.fallback = fallback
        self.fallback_count = 0

    def add_fallback(self, fallback: Callable[..., Any]) -> None:
        self.fallback = fallback

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        try:
            return self.primary(*args, **kwargs)
        except Exception as exc:
            logger.warning("Primary function failed, using fallback: %s", exc)
            self.fallback_count += 1
            return self.fallback(*args, **kwargs)
