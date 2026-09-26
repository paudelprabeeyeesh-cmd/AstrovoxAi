import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Belief:
    statement: str
    confidence: float = 0.5
    source: str = "default"
    last_verified: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class CommonSenseReasoningService:
    def __init__(self) -> None:
        self._beliefs: dict[str, Belief] = {}
        self._rules: list[dict[str, Any]] = []
        self._client = None
        self._load_default_beliefs()

    def _load_default_beliefs(self) -> None:
        defaults = [
            ("water_is_wet", 0.99, "default"),
            ("fire_is_hot", 0.99, "default"),
            ("ice_is_cold", 0.99, "default"),
            ("objects_fall_down", 0.99, "default"),
            ("day_follows_night", 0.99, "default"),
        ]
        for statement, confidence, source in defaults:
            self._beliefs[statement] = Belief(statement=statement, confidence=confidence, source=source)

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def add_belief(self, statement: str, belief: Any) -> None:
        if isinstance(belief, dict):
            conf = float(belief.get("confidence", 0.5))
            source = belief.get("source", "user")
            metadata = belief.get("metadata", {})
        else:
            conf = float(belief) if isinstance(belief, (int, float)) else 0.5
            source = "user"
            metadata = {}
        self._beliefs[statement] = Belief(statement=statement, confidence=conf, source=source, metadata=metadata)
        logger.debug("Added common-sense belief: %s = %.2f", statement, conf)

    def query(self, statement: str) -> Any:
        belief = self._beliefs.get(statement)
        if belief:
            return {"statement": belief.statement, "confidence": belief.confidence, "source": belief.source}
        return None

    def reason(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        applicable = self._find_applicable_beliefs(query)
        inferred = self._infer_common_sense(query, applicable, context)
        confidence = self._aggregate_confidence(inferred)
        return {
            "query": query,
            "applicable_beliefs": [b.statement for b in applicable],
            "inferences": inferred,
            "confidence": round(confidence, 4),
        }

    def add_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        self._rules.append(rule)
        logger.info("Added common-sense rule: %s", rule.get("name", "unnamed"))
        return {"status": "added", "rule_count": len(self._rules)}

    def verify_belief(self, statement: str) -> dict[str, Any]:
        belief = self._beliefs.get(statement)
        if not belief:
            return {"statement": statement, "status": "not_found", "confidence": 0.0}

        try:
            prompt = (
                "Verify whether the following common-sense statement is true. Return JSON with keys: verified (bool), confidence (float 0-1), reasoning (string).\n"
                f"Statement: {statement}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            import json
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            belief.confidence = float(data.get("confidence", belief.confidence))
            belief.last_verified = time.time()
            return {
                "statement": statement,
                "status": "verified",
                "verified": bool(data.get("verified", False)),
                "confidence": belief.confidence,
                "reasoning": data.get("reasoning", ""),
            }
        except Exception as exc:
            logger.error("Belief verification failed: %s", exc)
            return {"statement": statement, "status": "error", "error": str(exc)}

    def get_belief(self, statement: str) -> dict[str, Any] | None:
        belief = self._beliefs.get(statement)
        if not belief:
            return None
        return {
            "statement": belief.statement,
            "confidence": belief.confidence,
            "source": belief.source,
            "last_verified": belief.last_verified,
            "metadata": belief.metadata,
        }

    def list_beliefs(self) -> list[str]:
        return list(self._beliefs.keys())

    def _find_applicable_beliefs(self, query: str) -> list[Belief]:
        query_words = set(query.lower().split())
        scored = []
        for belief in self._beliefs.values():
            belief_words = set(belief.statement.lower().split())
            overlap = len(query_words & belief_words)
            scored.append((overlap, belief))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [b for _, b in scored[:5]]

    def _infer_common_sense(self, query: str, beliefs: list[Belief], context: dict[str, Any]) -> list[str]:
        if not beliefs:
            return []
        try:
            prompt = (
                "Given applicable common-sense beliefs, infer answers to the query. "
                "Return a JSON list of inference strings.\n"
                f"Query: {query}\nBeliefs: {[b.statement for b in beliefs]}\nContext: {context}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            import json
            content = response.choices[0].message.content or "[]"
            return [i for i in json.loads(content) if isinstance(i, str)]
        except Exception as exc:
            logger.error("Common-sense inference failed: %s", exc)
            return []

    def _aggregate_confidence(self, inferences: list[str]) -> float:
        if not inferences:
            return 0.0
        return round(min(1.0, 0.5 + 0.1 * len(inferences)), 4)
