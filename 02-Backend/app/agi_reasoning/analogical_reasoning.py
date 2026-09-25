import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Analogy:
    analogy_id: str
    source: str
    target: str
    score: float = 0.0
    mappings: dict[str, str] = field(default_factory=dict)
    explanation: str = ""
    created_at: float = field(default_factory=time.time)


class AnalogicalReasoningService:
    def __init__(self) -> None:
        self._analogies: dict[str, Analogy] = {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def find_analogy(self, source: str, target: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        score = self._compute_similarity(source, target)
        analogy_id = str(uuid.uuid4())
        mappings = self._structural_alignment(source, target)
        explanation = self._explain_analogy(source, target, mappings)
        analogy = Analogy(
            analogy_id=analogy_id,
            source=source,
            target=target,
            score=score,
            mappings=mappings,
            explanation=explanation,
        )
        self._analogies[analogy_id] = analogy
        logger.info("Found analogy %s with score %.4f", analogy_id, score)
        return {
            "analogy_id": analogy_id,
            "source": source,
            "target": target,
            "score": round(score, 4),
            "mappings": mappings,
            "explanation": explanation,
        }

    def structural_alignment(self, source: Any, target: Any) -> float:
        source_str = str(source)
        target_str = str(target)
        score = self._compute_similarity(source_str, target_str)
        return round(score, 4)

    def transfer_knowledge(self, source: str, target: str, knowledge: dict[str, Any]) -> dict[str, Any]:
        analogy_id = str(uuid.uuid4())
        transferred = self._apply_analogy_transfer(source, target, knowledge)
        analogy = Analogy(
            analogy_id=analogy_id,
            source=source,
            target=target,
            score=self._compute_similarity(source, target),
            mappings=transferred.get("mappings", {}),
            explanation=transferred.get("explanation", ""),
        )
        self._analogies[analogy_id] = analogy
        return {
            "analogy_id": analogy_id,
            "transferred_knowledge": transferred.get("transferred", {}),
            "confidence": transferred.get("confidence", 0.0),
        }

    def get_analogy(self, analogy_id: str) -> dict[str, Any] | None:
        analogy = self._analogies.get(analogy_id)
        if not analogy:
            return None
        return {
            "analogy_id": analogy.analogy_id,
            "source": analogy.source,
            "target": analogy.target,
            "score": analogy.score,
            "mappings": analogy.mappings,
            "explanation": analogy.explanation,
            "created_at": analogy.created_at,
        }

    def list_analogies(self) -> list[str]:
        return list(self._analogies.keys())

    def _compute_similarity(self, source: str, target: str) -> float:
        source_words = set(source.lower().split())
        target_words = set(target.lower().split())
        if not source_words or not target_words:
            return 0.0
        intersection = source_words & target_words
        union = source_words | target_words
        return len(intersection) / len(union)

    def _structural_alignment(self, source: str, target: str) -> dict[str, str]:
        try:
            prompt = (
                "Align the structure of the source domain to the target domain. "
                "Return JSON with a 'mappings' key: an object mapping source concepts to target concepts.\n"
                f"Source: {source}\nTarget: {target}"
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
            mappings = data.get("mappings", {})
            return {k: v for k, v in mappings.items() if isinstance(k, str) and isinstance(v, str)}
        except Exception as exc:
            logger.error("Structural alignment failed: %s", exc)
            return {}

    def _explain_analogy(self, source: str, target: str, mappings: dict[str, str]) -> str:
        try:
            prompt = (
                "Explain the analogy between the source and target based on the mappings. Return a concise explanation string.\n"
                f"Source: {source}\nTarget: {target}\nMappings: {mappings}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content or "No explanation available."
        except Exception as exc:
            logger.error("Analogy explanation failed: %s", exc)
            return "Explanation unavailable."

    def _apply_analogy_transfer(self, source: str, target: str, knowledge: dict[str, Any]) -> dict[str, Any]:
        mappings = self._structural_alignment(source, target)
        transferred = {}
        for source_key, target_key in mappings.items():
            if source_key in knowledge:
                transferred[target_key] = knowledge[source_key]
        return {
            "transferred": transferred,
            "mappings": mappings,
            "confidence": self._compute_similarity(source, target),
            "explanation": self._explain_analogy(source, target, mappings),
        }
