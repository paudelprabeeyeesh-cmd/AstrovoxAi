from abc import ABC, abstractmethod
from typing import Any, Dict


class PluginBase(ABC):
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
