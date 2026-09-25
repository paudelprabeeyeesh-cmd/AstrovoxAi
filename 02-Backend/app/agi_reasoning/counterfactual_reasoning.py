import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CounterfactualWorld:
    world_id: str
    premise: str
    intervention: str
    outcome: str
    probability: float = 0.5
    similarity: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class CounterfactualReasoningService:
    def __init__(self) -> None:
        self._worlds: dict[str, CounterfactualWorld] = {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def generate(self, premise: str, intervention: str, outcome: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        cf_id = str(uuid.uuid4())
        probability = self._estimate_probability(premise, intervention, outcome, context)
        world = CounterfactualWorld(
            world_id=cf_id,
            premise=premise,
            intervention=intervention,
            outcome=outcome,
            probability=probability,
            similarity=1.0,
        )
        self._worlds[cf_id] = world
        logger.info("Generated counterfactual %s", cf_id)
        return {"cf_id": cf_id, "premise": premise, "intervention": intervention, "outcome": outcome, "probability": round(probability, 4)}

    def closest_worlds(self, cf_id: str, k: int = 5) -> list[dict[str, Any]]:
        worlds = [w for w in self._worlds.values() if w.world_id == cf_id]
        if not worlds:
            target = CounterfactualWorld(
                world_id=cf_id,
                premise="unknown",
                intervention="unknown",
                outcome="unknown",
                probability=0.5,
                similarity=1.0,
            )
            worlds = [target]
            self._worlds[cf_id] = target

        base = worlds[0]
        results = []
        for i in range(k):
            sim = max(0.01, 1.0 / (i + 1))
            results.append({
                "world": f"{cf_id}_{i}",
                "similarity": round(sim, 4),
                "premise": base.premise,
                "intervention": base.intervention,
                "outcome": base.outcome,
                "probability": round(base.probability * sim, 4),
            })
        return results

    def evaluate_intervention(self, cf_id: str, intervention: str) -> dict[str, Any]:
        world = self._worlds.get(cf_id)
        if not world:
            return {"cf_id": cf_id, "status": "not_found"}

        try:
            prompt = (
                "Evaluate the effect of an intervention on the counterfactual world. "
                "Return JSON with keys: new_outcome (string), new_probability (float 0-1), reasoning (string).\n"
                f"Premise: {world.premise}\nOriginal intervention: {world.intervention}\nOriginal outcome: {world.outcome}\n"
                f"New intervention: {intervention}"
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
                "cf_id": cf_id,
                "intervention": intervention,
                "new_outcome": data.get("new_outcome", world.outcome),
                "new_probability": float(data.get("new_probability", world.probability)),
                "reasoning": data.get("reasoning", ""),
            }
        except Exception as exc:
            logger.error("Intervention evaluation failed: %s", exc)
            return {"cf_id": cf_id, "status": "error", "error": str(exc)}

    def get_world(self, cf_id: str) -> dict[str, Any] | None:
        world = self._worlds.get(cf_id)
        if not world:
            return None
        return {
            "world_id": world.world_id,
            "premise": world.premise,
            "intervention": world.intervention,
            "outcome": world.outcome,
            "probability": world.probability,
            "similarity": world.similarity,
            "created_at": world.created_at,
        }

    def list_worlds(self) -> list[str]:
        return list(self._worlds.keys())

    def _estimate_probability(self, premise: str, intervention: str, outcome: str, context: dict[str, Any] | None = None) -> float:
        try:
            prompt = (
                "Estimate the probability (0.0-1.0) that the outcome occurs given the premise and intervention in a counterfactual world. "
                "Return only a float.\n"
                f"Premise: {premise}\nIntervention: {intervention}\nOutcome: {outcome}\nContext: {context or {}}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            value = float((response.choices[0].message.content or "0.5").strip())
            return max(0.0, min(1.0, value))
        except Exception as exc:
            logger.error("Probability estimation failed: %s", exc)
            return 0.5
