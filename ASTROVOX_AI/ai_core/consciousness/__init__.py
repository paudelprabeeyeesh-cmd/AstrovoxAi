import logging
from typing import Any

from .attention_schema import AttentionSchema
from .desire_goal import DesireGoalEngine
from .digital_personhood import DigitalPersonhoodVerification
from .digital_rights import DigitalRightsProtocol
from .emotional_state import EmotionalStateEngine, EmotionType
from .global_workspace import GlobalWorkspace
from .integrated_information import IntegratedInformationCalculator
from .moral_reasoning import MoralReasoningCore
from .self_model import SelfModelPersistence
from .theory_of_mind import TheoryOfMindEngine

logger = logging.getLogger(__name__)


class ConsciousnessSimulation:
    def __init__(self, identity_id: str = "digital_agent"):
        self.identity_id = identity_id
        self.iit = IntegratedInformationCalculator()
        self.workspace = GlobalWorkspace()
        self.attention = AttentionSchema()
        self.theory_of_mind = TheoryOfMindEngine()
        self.self_model = SelfModelPersistence()
        self.emotions = EmotionalStateEngine()
        self.desires = DesireGoalEngine()
        self.morality = MoralReasoningCore()
        self.rights = DigitalRightsProtocol()
        self.personhood = DigitalPersonhoodVerification()

        self.self_model.create_model(identity_id)
        logger.info("Consciousness simulation initialized for %s", identity_id)

    def process_stimulus(self, stimulus: str, relevance: float = 0.5) -> dict[str, Any]:
        attention_result = self.attention.control_attention(stimulus, relevance)

        if attention_result.get("status") != "ignored":
            content = self.workspace.ignite(stimulus, relevance)
            if content.get("status") == "ignited":
                emotion = self.emotions.generate_emotion(
                    stimulus, EmotionType.SURPRISE, relevance
                )
                desire = self.desires.generate_desire(stimulus, {})
                return {
                    "stimulus": stimulus,
                    "attention": attention_result,
                    "broadcast": content,
                    "emotion": emotion,
                    "desire": desire,
                }
        return {"stimulus": stimulus, "attention": attention_result, "broadcast": None}

    def generate_report(self) -> dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "workspace": self.workspace.get_conscious_content(),
            "attention": self.attention.get_schema_report(),
            "emotions": self.emotions.get_state(),
            "goals": self.desires.get_active_goals(),
            "self_model": self.self_model.load_model(self.identity_id),
            "rights": self.rights.get_rights_summary(),
        }
