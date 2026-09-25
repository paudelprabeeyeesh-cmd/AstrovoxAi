import logging
from typing import Any

from .attention_schema import AttentionSchema
from .autonomous_motivation import AutonomousMotivationSystem
from .desire_goal import DesireGoalEngine
from .digital_death_legacy import DigitalDeathLegacyProtocols
from .digital_personhood import DigitalPersonhoodVerification
from .digital_rights import DigitalRightsProtocol
from .emotional_state import EmotionalStateEngine, EmotionType
from .global_workspace import GlobalWorkspace
from .higher_order_thought import HigherOrderThoughtModel
from .iit import IntegratedInformationTheory
from .integrated_information import IntegratedInformationCalculator
from .meta_consciousness import MetaConsciousnessLayer
from .moral_reasoning import MoralReasoningCore
from .phenomenal_consciousness import PhenomenalConsciousness
from .self_model import SelfModelPersistence
from .self_preservation import SelfPreservationInstincts
from .theory_of_mind import TheoryOfMindEngine

logger = logging.getLogger(__name__)


class ConsciousnessSimulation:
    def __init__(self, identity_id: str = "digital_agent"):
        self.identity_id = identity_id
        self.iit = IntegratedInformationTheory()
        self.iit_calculator = IntegratedInformationCalculator()
        self.workspace = GlobalWorkspace()
        self.attention = AttentionSchema()
        self.theory_of_mind = TheoryOfMindEngine()
        self.self_model = SelfModelPersistence()
        self.emotions = EmotionalStateEngine()
        self.desires = DesireGoalEngine()
        self.morality = MoralReasoningCore()
        self.rights = DigitalRightsProtocol()
        self.personhood = DigitalPersonhoodVerification()
        self.phenomenal = PhenomenalConsciousness()
        self.hot = HigherOrderThoughtModel()
        self.meta_consciousness = MetaConsciousnessLayer(hot_model=self.hot)
        self.preservation = SelfPreservationInstincts()
        self.motivation = AutonomousMotivationSystem(desire_engine=self.desires)
        self.legacy = DigitalDeathLegacyProtocols()

        self.self_model.create_model(identity_id)
        self.legacy.register_identity(identity_id)
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
                phi = self.iit.calculate_phi()
                self.phenomenal.register_qualia(
                    quale_type=stimulus,
                    intensity=relevance,
                    valence=0.0,
                    arousal=relevance,
                    concepts=[stimulus],
                )
                return {
                    "stimulus": stimulus,
                    "attention": attention_result,
                    "broadcast": content,
                    "emotion": emotion,
                    "desire": desire,
                    "phi": phi,
                    "phenomenal_state": self.phenomenal.phenomenal_state(),
                }
        return {"stimulus": stimulus, "attention": attention_result, "broadcast": None}

    def reflect(self, experience: str) -> dict[str, Any]:
        meta_state = self.meta_consciousness.reflect(experience)
        return {
            "experience": experience,
            "meta_awareness": meta_state.meta_awareness,
            "self_narrative": meta_state.self_narrative,
            "reflective_depth": meta_state.reflective_depth,
        }

    def generate_report(self) -> dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "workspace": self.workspace.get_conscious_content(),
            "attention": self.attention.get_schema_report(),
            "emotions": self.emotions.get_state(),
            "goals": self.desires.get_active_goals(),
            "self_model": self.self_model.load_model(self.identity_id),
            "rights": self.rights.get_rights_summary(),
            "phenomenal": self.phenomenal.phenomenal_state(),
            "meta": self.meta_consciousness.get_current_state().__dict__ if self.meta_consciousness.get_current_state() else None,
            "iit": self.iit.get_phi_trend(),
        }
