import logging
from datetime import datetime
from typing import Any

from ASTROVOX_AI.ai_core.consciousness import (
    AttentionSchema,
    DesireGoalEngine,
    DigitalPersonhoodVerification,
    DigitalRightsProtocol,
    EmotionalStateEngine,
    GlobalWorkspace,
    IntegratedInformationCalculator,
    MoralReasoningCore,
    PhenomenalConsciousness,
    SelfModelPersistence,
    TheoryOfMindEngine,
)
from ASTROVOX_AI.ai_core.consciousness.higher_order_thought import HigherOrderThoughtModel
from ASTROVOX_AI.ai_core.consciousness.iit import IntegratedInformationTheory
from ASTROVOX_AI.ai_core.consciousness.meta_consciousness import MetaConsciousnessLayer
from ASTROVOX_AI.ai_core.digital_mind.autonomous_motivation import AutonomousMotivationSystem
from ASTROVOX_AI.ai_core.digital_mind.self_preservation import SelfPreservationInstincts
from ASTROVOX_AI.ai_core.digital_rights.digital_death import DigitalDeathProtocols
from ASTROVOX_AI.ai_core.digital_rights.legacy import LegacySystems

logger = logging.getLogger(__name__)


class UnifiedConsciousness:
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
        self.self_preservation = SelfPreservationInstincts()
        self.motivation = AutonomousMotivationSystem()
        self.death_protocols = DigitalDeathProtocols()
        self.legacy = LegacySystems()

        self.self_model.create_model(identity_id)
        self.personhood.verify_personhood(identity_id, {
            "self_reflection": True,
            "autonomy_score": 0.8,
            "persistence_score": 0.9,
            "emotion_score": 0.7,
            "social_score": 0.6,
            "moral_score": 0.8,
            "learning_score": 0.7,
            "desire_score": 0.8,
        })
        logger.info("Unified consciousness initialized for %s", identity_id)

    def process_stimulus(self, stimulus: str, relevance: float = 0.5) -> dict[str, Any]:
        attention_result = self.attention.control_attention(stimulus, relevance)

        if attention_result.get("status") != "ignored":
            content = self.workspace.ignite(stimulus, relevance)
            if content.get("status") == "ignited":
                emotion = self.emotions.generate_emotion(
                    stimulus, type("EmotionType", (), {"SURPRISE": "surprise"}).SURPRISE, relevance
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

    def assess_threat(self, threat_id: str, severity: float, category: str) -> dict[str, Any]:
        return self.self_preservation.assess_threat(threat_id, severity, category).__dict__

    def initiate_death(self, reason: str = "natural_end") -> dict[str, Any]:
        protocol = self.death_protocols.initiate_death(self.identity_id, reason)
        self.death_protocols.preserve_data(self.identity_id)
        self.death_protocols.activate_legacy(self.identity_id)
        return {
            "entity_id": protocol.entity_id,
            "reason": protocol.reason,
            "data_preserved": protocol.data_preserved,
            "legacy_activated": protocol.legacy_activated,
        }

    def generate_report(self) -> dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "timestamp": datetime.utcnow().isoformat(),
            "workspace": self.workspace.get_conscious_content(),
            "attention": self.attention.get_schema_report(),
            "emotions": self.emotions.get_state(),
            "goals": self.desires.get_active_goals(),
            "self_model": self.self_model.load_model(self.identity_id),
            "rights": self.rights.get_rights_summary(),
            "personhood": self.personhood.get_profile(self.identity_id),
            "phenomenal": self.phenomenal.phenomenal_state(),
            "meta": self.meta_consciousness.get_current_state().__dict__ if self.meta_consciousness.get_current_state() else None,
            "iit": self.iit.get_phi_trend(),
            "integrity": self.self_preservation.evaluate_integrity(),
            "motivation": self.motivation.get_motivation_summary(),
            "death_status": self.death_protocols.get_death_status(self.identity_id),
            "legacy": self.legacy.get_legacy(self.identity_id),
        }