import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FeatureCandidate:
    feature_id: str
    name: str
    description: str
    impact: float = 0.0
    complexity: float = 0.0
    status: str = "proposed"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class AutonomousFeatureDevService:
    def __init__(self) -> None:
        self._features: dict[str, FeatureCandidate] = {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def propose(self, candidate: dict[str, Any]) -> dict[str, Any]:
        feature_id = candidate.get("feature_id") or str(uuid.uuid4())
        feature = FeatureCandidate(
            feature_id=feature_id,
            name=candidate.get("name", "unnamed_feature"),
            description=candidate.get("description", ""),
            impact=float(candidate.get("impact", 0.0)),
            complexity=float(candidate.get("complexity", 0.0)),
            status="proposed",
            metadata=candidate.get("metadata", {}),
        )
        self._features[feature_id] = feature
        logger.info("Proposed feature %s: %s", feature_id, feature.name)
        return {"status": "proposed", "feature": feature.name, "feature_id": feature_id}

    def prioritize(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prioritized = sorted(candidates, key=lambda c: c.get("impact", 0.0), reverse=True)
        ranked = []
        for idx, candidate in enumerate(prioritized, start=1):
            feature_id = candidate.get("feature_id") or str(uuid.uuid4())
            if feature_id in self._features:
                self._features[feature_id].status = "prioritized"
            ranked.append({"rank": idx, "feature_id": feature_id, "name": candidate.get("name"), "impact": candidate.get("impact", 0.0)})
        return ranked

    def deploy(self, candidate: dict[str, Any]) -> dict[str, Any]:
        feature_id = candidate.get("feature_id")
        if not feature_id:
            return {"status": "error", "reason": "missing_feature_id"}
        feature = self._features.get(feature_id)
        if not feature:
            return {"status": "not_found", "feature_id": feature_id}
        feature.status = "deployed"
        logger.info("Deployed feature %s", feature_id)
        return {"status": "deployed", "feature": feature.name, "feature_id": feature_id}

    def analyze_gap(self, current_features: list[str], user_feedback: str) -> dict[str, Any]:
        try:
            prompt = (
                "Analyze the gap between current features and user feedback. Return JSON with keys: "
                "suggested_features (list of strings), priority (string), rationale (string).\n"
                f"Current features: {current_features}\nUser feedback: {user_feedback}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            import json
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return {
                "suggested_features": data.get("suggested_features", []),
                "priority": data.get("priority", "medium"),
                "rationale": data.get("rationale", ""),
            }
        except Exception as exc:
            logger.error("Gap analysis failed: %s", exc)
            return {"suggested_features": [], "priority": "medium", "error": str(exc)}

    def get_feature(self, feature_id: str) -> dict[str, Any] | None:
        feature = self._features.get(feature_id)
        if not feature:
            return None
        return {
            "feature_id": feature.feature_id,
            "name": feature.name,
            "description": feature.description,
            "impact": feature.impact,
            "complexity": feature.complexity,
            "status": feature.status,
            "metadata": feature.metadata,
            "created_at": feature.created_at,
        }

    def list_features(self, status: str | None = None) -> list[str]:
        features = list(self._features.values())
        if status:
            features = [f for f in features if f.status == status]
        return [f.feature_id for f in features]
