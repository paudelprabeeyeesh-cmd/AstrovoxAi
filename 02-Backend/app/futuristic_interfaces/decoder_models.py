import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DecoderModelConfig:
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_type: str = "thought_to_text"
    output_type: str = "text"
    latency_ms: float = 120.0
    version: str = "1.0.0"
    accuracy: float = 0.85
    metadata: dict[str, Any] = field(default_factory=dict)


class DecoderModelService:
    MODELS = {
        "thought_to_text": {"type": "sequence", "output": "text", "latency_ms": 120, "accuracy": 0.82, "version": "1.2.0"},
        "motor_imagery": {"type": "classification", "output": "command", "latency_ms": 80, "accuracy": 0.88, "version": "1.1.0"},
        "emotion": {"type": "regression", "output": "emotion_scores", "latency_ms": 60, "accuracy": 0.79, "version": "1.0.0"},
        "speech_production": {"type": "sequence", "output": "audio_features", "latency_ms": 150, "accuracy": 0.75, "version": "0.9.0"},
        "visual_decoding": {"type": "generation", "output": "image", "latency_ms": 300, "accuracy": 0.65, "version": "0.8.0"},
        "memory_retrieval": {"type": "retrieval", "output": "memory_vector", "latency_ms": 90, "accuracy": 0.80, "version": "1.0.0"},
        "attention_focus": {"type": "regression", "output": "focus_score", "latency_ms": 45, "accuracy": 0.85, "version": "1.0.0"},
    }

    def __init__(self) -> None:
        self._predictions: dict[str, dict[str, Any]] = {}

    def predict(self, model_type: str, input_data: dict[str, Any]) -> dict[str, Any]:
        model = self.MODELS.get(model_type)
        if not model:
            raise ValueError(f"Unknown model type: {model_type}")
        start = time.time()
        result = self._simulate_output(model_type, input_data)
        latency = (time.time() - start) * 1000.0
        prediction_id = str(uuid.uuid4())
        output = {
            "model_type": model_type,
            "prediction_id": prediction_id,
            "output": model["output"],
            "result": result,
            "latency_ms": round(latency, 2),
            "model_version": model["version"],
            "accuracy": model["accuracy"],
            "timestamp": time.time(),
        }
        self._predictions[prediction_id] = output
        return output

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {
                "model_type": k,
                "output": v["output"],
                "latency_ms": v["latency_ms"],
                "accuracy": v["accuracy"],
                "version": v["version"],
            }
            for k, v in self.MODELS.items()
        ]

    def get_model(self, model_type: str) -> dict[str, Any]:
        model = self.MODELS.get(model_type)
        if not model:
            raise ValueError(f"Unknown model type: {model_type}")
        return {
            "model_type": model_type,
            "type": model["type"],
            "output": model["output"],
            "latency_ms": model["latency_ms"],
            "accuracy": model["accuracy"],
            "version": model["version"],
        }

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        items = sorted(self._predictions.values(), key=lambda x: x["timestamp"], reverse=True)
        return items[:limit]

    def _simulate_output(self, model_type: str, input_data: dict[str, Any]) -> Any:
        if model_type == "thought_to_text":
            embedding = input_data.get("neural_embedding", [])
            seed = sum(embedding) if embedding else 0.0
            words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog"]
            return [" ".join(words[int(abs(seed + i)) % len(words):int(abs(seed + i + 3)) % len(words) + 3]) for i in range(input_data.get("top_k", 1))]
        if model_type == "motor_imagery":
            return {"command": "rest", "confidence": 0.85, "features": {"theta_over_beta": 0.45}}
        if model_type == "emotion":
            return {"joy": 0.2, "sadness": 0.1, "anger": 0.05, "fear": 0.15, "surprise": 0.1, "neutral": 0.4}
        if model_type == "speech_production":
            return {"phonemes": ["a", "e", "i"], "prosody": "neutral", "text": "placeholder speech"}
        if model_type == "visual_decoding":
            return {"image_prompt": "abstract neural pattern", "style": "neuro_art", "confidence": 0.6}
        if model_type == "memory_retrieval":
            return {"memory_vector": [0.1, 0.2, 0.3], "relevance": 0.75}
        if model_type == "attention_focus":
            return {"focus_score": 0.7, "distraction_level": 0.3}
        return {}
