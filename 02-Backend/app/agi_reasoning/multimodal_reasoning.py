import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModalityInput:
    modality: str
    data: Any
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class FusedOutput:
    fused_id: str
    modalities: list[str]
    result: dict[str, Any]
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


class MultimodalReasoningService:
    def __init__(self) -> None:
        self._inputs: list[ModalityInput] = []
        self._outputs: dict[str, FusedOutput] = {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def fuse(self, inputs: dict[str, Any], fusion_strategy: str = "attention") -> dict[str, Any]:
        modality_inputs = []
        for modality, data in inputs.items():
            modality_inputs.append(ModalityInput(modality=modality, data=data))
        self._inputs.extend(modality_inputs)

        fused_id = str(uuid.uuid4())
        result = self._compute_fusion(modality_inputs, fusion_strategy)
        confidence = self._aggregate_confidence(modality_inputs)
        output = FusedOutput(fused_id=fused_id, modalities=list(inputs.keys()), result=result, confidence=confidence)
        self._outputs[fused_id] = output

        return {
            "fused_id": fused_id,
            "fused": True,
            "modalities": list(inputs.keys()),
            "result": result,
            "confidence": round(confidence, 4),
            "strategy": fusion_strategy,
        }

    def reason(self, fused_id: str, query: str) -> dict[str, Any]:
        output = self._outputs.get(fused_id)
        if not output:
            return {"fused_id": fused_id, "status": "not_found"}

        try:
            prompt = (
                "Given the fused multimodal data, answer the query. Return JSON with keys: answer (string), confidence (float 0-1), reasoning (string).\n"
                f"Modalities: {output.modalities}\nData: {output.result}\nQuery: {query}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            import json
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return {
                "fused_id": fused_id,
                "query": query,
                "answer": data.get("answer", ""),
                "confidence": float(data.get("confidence", 0.0)),
                "reasoning": data.get("reasoning", ""),
            }
        except Exception as exc:
            logger.error("Reasoning failed: %s", exc)
            return {"fused_id": fused_id, "status": "error", "error": str(exc)}

    def get_output(self, fused_id: str) -> dict[str, Any] | None:
        output = self._outputs.get(fused_id)
        if not output:
            return None
        return {
            "fused_id": output.fused_id,
            "modalities": output.modalities,
            "result": output.result,
            "confidence": output.confidence,
            "timestamp": output.timestamp,
        }

    def list_outputs(self) -> list[str]:
        return list(self._outputs.keys())

    def _compute_fusion(self, inputs: list[ModalityInput], strategy: str) -> dict[str, Any]:
        if not inputs:
            return {}
        if strategy == "concat":
            combined = " ".join(str(i.data) for i in inputs)
            return {"text": combined}
        if strategy == "max":
            return {"dominant_modality": max(inputs, key=lambda i: i.confidence).modality, "data": max(inputs, key=lambda i: i.confidence).data}

        weights = [i.confidence for i in inputs]
        total = sum(weights)
        if total == 0:
            weights = [1.0 / len(inputs)] * len(inputs)
        else:
            weights = [w / total for w in weights]
        return {
            "weighted_modalities": {i.modality: round(weights[idx], 4) for idx, i in enumerate(inputs)},
            "dominant": inputs[weights.index(max(weights))].modality,
            "input_count": len(inputs),
        }

    def _aggregate_confidence(self, inputs: list[ModalityInput]) -> float:
        if not inputs:
            return 0.0
        total = sum(i.confidence for i in inputs)
        return round(total / len(inputs), 4)
