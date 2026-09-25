import logging
from typing import Any

from app.agi_reasoning.analogical_reasoning import AnalogicalReasoningService
from app.agi_reasoning.causal_reasoning import CausalReasoningService
from app.agi_reasoning.common_sense_reasoning import CommonSenseReasoningService
from app.agi_reasoning.counterfactual_reasoning import CounterfactualReasoningService
from app.agi_reasoning.meta_learning import MetaLearningService
from app.agi_reasoning.multimodal_reasoning import MultimodalReasoningService
from app.agi_reasoning.recursive_self_improvement import RecursiveSelfImprovementService
from app.agi_reasoning.theory_of_mind import TheoryOfMindService

logger = logging.getLogger(__name__)


class AGIReasoningService:
    def __init__(self) -> None:
        self.engines: dict[str, Any] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.engines["recursive_self_improvement"] = RecursiveSelfImprovementService()
        self.engines["meta_learning"] = MetaLearningService()
        self.engines["theory_of_mind"] = TheoryOfMindService()
        self.engines["causal_reasoning"] = CausalReasoningService()
        self.engines["counterfactual_reasoning"] = CounterfactualReasoningService()
        self.engines["analogical_reasoning"] = AnalogicalReasoningService()
        self.engines["common_sense_reasoning"] = CommonSenseReasoningService()
        self.engines["multimodal_reasoning"] = MultimodalReasoningService()

    def register(self, name: str, engine: Any) -> None:
        self.engines[name] = engine

    def query(self, engine_name: str, query: str) -> dict[str, Any]:
        engine = self.engines.get(engine_name)
        if not engine:
            return {"error": f"Engine '{engine_name}' not found"}
        method = getattr(engine, "query", None)
        if callable(method):
            return method("__default__", query)
        return {"engine": engine_name, "query": query, "status": "ok"}
