import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DegradationManager:
    def __init__(self) -> None:
        self._fallbacks: Dict[str, List[Callable]] = {}
        self._degraded_services: set[str] = set()
        self._circuit_breakers: Dict[str, Any] = {}

    def register_fallback(self, service: str, fallback_func: Callable) -> None:
        if service not in self._fallbacks:
            self._fallbacks[service] = []
        self._fallbacks[service].append(fallback_func)
        logger.info(f"Registered fallback for service: {service}")

    def execute_with_fallback(self, service: str, func: Callable, *args: Any, **kwargs: Any) -> Any:
        try:
            result = func(*args, **kwargs)
            self._degraded_services.discard(service)
            return result
        except Exception as e:
            logger.warning(f"Service {service} failed: {e}")
            self._degraded_services.add(service)
            if service in self._fallbacks:
                for fallback in self._fallbacks[service]:
                    try:
                        logger.info(f"Executing fallback for service: {service}")
                        return fallback(*args, **kwargs)
                    except Exception as fallback_e:
                        logger.warning(f"Fallback for {service} failed: {fallback_e}")
                        continue
            raise

    def get_degradation_status(self) -> Dict[str, Any]:
        return {
            "degraded_services": list(self._degraded_services),
            "registered_fallbacks": list(self._fallbacks.keys()),
            "status": "degraded" if self._degraded_services else "healthy",
        }
