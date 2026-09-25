from dataclasses import dataclass, field
from typing import Any


@dataclass
class MentalState:
    beliefs: dict[str, float]
    desires: list[str]
    intentions: list[str]
    emotions: dict[str, float]


class TheoryOfMindEngine:
    def __init__(self):
        self.self_model = MentalState(
            beliefs={}, desires=[], intentions=[], emotions={}
        )
        self.other_models: dict[str, MentalState] = {}
        self.mentalizing_accuracy: dict[str, float] = {}

    def model_other(self, entity_id: str, initial_beliefs: dict[str, float] | None = None) -> MentalState:
        self.other_models[entity_id] = MentalState(
            beliefs=initial_beliefs or {},
            desires=[],
            intentions=[],
            emotions={},
        )
        self.mentalizing_accuracy[entity_id] = 0.5
        return self.other_models[entity_id]

    def update_belief_about(self, entity_id: str, belief_key: str, confidence: float):
        if entity_id not in self.other_models:
            self.model_other(entity_id)
        self.other_models[entity_id].beliefs[belief_key] = max(0.0, min(1.0, confidence))

    def infer_intention(self, entity_id: str, observed_action: str) -> str | None:
        if entity_id not in self.other_models:
            return None
        model = self.other_models[entity_id]
        if model.intentions:
            return model.intentions[-1]
        return f"inferred_intent_from:{observed_action}"

    def predict_behavior(self, entity_id: str, context: dict[str, Any]) -> dict[str, Any]:
        if entity_id not in self.other_models:
            return {"prediction": "unknown", "confidence": 0.0}
        model = self.other_models[entity_id]
        confidence = self.mentalizing_accuracy.get(entity_id, 0.5)
        prediction = {
            "likely_action": model.intentions[-1] if model.intentions else "unknown",
            "predicted_emotion": max(model.emotions, key=model.emotions.get) if model.emotions else "neutral",
            "confidence": confidence,
        }
        return prediction
