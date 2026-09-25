import logging
from typing import Any

logger = logging.getLogger(__name__)


class DecoderModelService:
    MODELS = {
        "thought_to_text": {"type": "sequence", "output": "text", "latency_ms": 120},
        "motor_imagery": {"type": "classification", "output": "command", "latency_ms": 80},
        "emotion": {"type": "regression", "output": "emotion_scores", "latency_ms": 60},
        "speech_production": {"type": "sequence", "output": "audio_features", "latency_ms": 150},
        "visual_decoding": {"type": "generation", "output": "image", "latency_ms": 300},
    }

    def predict(self, model_type: str, input_data: dict[str, Any]) -> dict[str, Any]:
        model = self.MODELS.get(model_type)
        if not model:
            raise ValueError(f"Unknown model type: {model_type}")
        return {
            "model_type": model_type,
            "output": model["output"],
            "result": self._simulate_output(model_type, input_data),
            "latency_ms": model["latency_ms"],
        }

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {"model_type": k, **v}
            for k, v in self.MODELS.items()
        ]

    def _simulate_output(self, model_type: str, input_data: dict[str, Any]) -> Any:
        if model_type == "thought_to_text":
            return ["placeholder thought"]
        if model_type == "motor_imagery":
            return {"command": "rest", "confidence": 0.85}
        if model_type == "emotion":
            return {"joy": 0.2, "neutral": 0.6, "focus": 0.2}
        if model_type == "speech_production":
            return {"phonemes": ["a", "e", "i"], "prosody": "neutral"}
        if model_type == "visual_decoding":
            return {"image_prompt": "abstract neural pattern", "style": "neuro_art"}
        return {}
