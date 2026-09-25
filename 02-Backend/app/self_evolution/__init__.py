import logging
from typing import Any

from app.self_evolution.autonomous_feature_dev import AutonomousFeatureDevService
from app.self_evolution.evolutionary_architecture import EvolutionaryArchitectureService
from app.self_evolution.hypothesis_generator import HypothesisGeneratorService
from app.self_evolution.self_debugging import SelfDebuggingService
from app.self_evolution.self_modifying_code import SelfModifyingCodeService

logger = logging.getLogger(__name__)


class SelfEvolutionService:
    def __init__(self) -> None:
        self.modules: dict[str, Any] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.modules["autonomous_feature_dev"] = AutonomousFeatureDevService()
        self.modules["evolutionary_architecture"] = EvolutionaryArchitectureService()
        self.modules["hypothesis_generator"] = HypothesisGeneratorService()
        self.modules["self_debugging"] = SelfDebuggingService()
        self.modules["self_modifying_code"] = SelfModifyingCodeService()

    def register(self, name: str, module: Any) -> None:
        self.modules[name] = module

    def get(self, name: str) -> Any | None:
        return self.modules.get(name)

    def act(self, module_name: str, action: str, args: dict[str, Any]) -> Any:
        module = self.modules.get(module_name)
        if not module:
            raise ValueError(f"Module '{module_name}' not found")
        handler = getattr(module, action, None)
        if not callable(handler):
            raise ValueError(f"Unsupported action '{action}' for module '{module_name}'")
        return handler(**args)
