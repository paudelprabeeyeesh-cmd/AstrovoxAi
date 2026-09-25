import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    experiment_id: str
    hypothesis_id: str
    description: str
    variables: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)


@dataclass
class Hypothesis:
    hypothesis_id: str
    description: str
    prior_probability: float = 0.5
    evidence: list[dict[str, Any]] = field(default_factory=list)
    posterior_probability: float = 0.5
    status: str = "generated"
    created_at: float = field(default_factory=time.time)


class HypothesisGeneratorService:
    def __init__(self) -> None:
        self._hypotheses: dict[str, Hypothesis] = {}
        self._experiments: dict[str, Experiment] = {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def generate(self, hypothesis_id: str, description: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        hypothesis = Hypothesis(
            hypothesis_id=hypothesis_id,
            description=description,
            prior_probability=self._estimate_prior(description, context),
        )
        self._hypotheses[hypothesis_id] = hypothesis
        logger.info("Generated hypothesis %s", hypothesis_id)
        return {
            "hypothesis_id": hypothesis_id,
            "description": description,
            "status": "generated",
            "prior_probability": round(hypothesis.prior_probability, 4),
        }

    def evaluate(self, hypothesis_id: str, result: dict[str, Any]) -> dict[str, Any]:
        hypothesis = self._hypotheses.get(hypothesis_id)
        if not hypothesis:
            return {"hypothesis_id": hypothesis_id, "status": "not_found"}

        posterior = self._compute_posterior(hypothesis, result)
        hypothesis.posterior_probability = posterior
        hypothesis.evidence.append(result)
        hypothesis.status = "evaluated"
        logger.info("Evaluated hypothesis %s: posterior=%.4f", hypothesis_id, posterior)
        return {"hypothesis_id": hypothesis_id, "posterior": round(posterior, 4), "result": result}

    def run_experiment(self, hypothesis_id: str, variables: dict[str, Any]) -> dict[str, Any]:
        hypothesis = self._hypotheses.get(hypothesis_id)
        if not hypothesis:
            return {"experiment_id": "", "status": "not_found"}

        experiment_id = str(uuid.uuid4())
        experiment = Experiment(
            experiment_id=experiment_id,
            hypothesis_id=hypothesis_id,
            description=hypothesis.description,
            variables=variables,
        )
        self._experiments[experiment_id] = experiment
        experiment.status = "running"
        logger.info("Started experiment %s for hypothesis %s", experiment_id, hypothesis_id)
        return {"experiment_id": experiment_id, "hypothesis_id": hypothesis_id, "status": "running"}

    def conclude_experiment(self, experiment_id: str, conclusion: dict[str, Any]) -> dict[str, Any]:
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return {"experiment_id": experiment_id, "status": "not_found"}

        experiment.results = conclusion
        experiment.status = "completed"
        experiment.confidence = float(conclusion.get("confidence", 0.0))

        hypothesis = self._hypotheses.get(experiment.hypothesis_id)
        if hypothesis:
            hypothesis.evidence.append(conclusion)
            hypothesis.posterior_probability = self._compute_posterior(hypothesis, conclusion)

        logger.info("Concluded experiment %s", experiment_id)
        return {
            "experiment_id": experiment_id,
            "hypothesis_id": experiment.hypothesis_id,
            "status": "completed",
            "confidence": experiment.confidence,
        }

    def get_hypothesis(self, hypothesis_id: str) -> dict[str, Any] | None:
        hypothesis = self._hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None
        return {
            "hypothesis_id": hypothesis.hypothesis_id,
            "description": hypothesis.description,
            "prior_probability": hypothesis.prior_probability,
            "posterior_probability": hypothesis.posterior_probability,
            "evidence_count": len(hypothesis.evidence),
            "status": hypothesis.status,
        }

    def list_hypotheses(self) -> list[str]:
        return list(self._hypotheses.keys())

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None
        return {
            "experiment_id": experiment.experiment_id,
            "hypothesis_id": experiment.hypothesis_id,
            "description": experiment.description,
            "variables": experiment.variables,
            "results": experiment.results,
            "status": experiment.status,
            "confidence": experiment.confidence,
        }

    def list_experiments(self, hypothesis_id: str | None = None) -> list[str]:
        experiments = list(self._experiments.values())
        if hypothesis_id:
            experiments = [e for e in experiments if e.hypothesis_id == hypothesis_id]
        return [e.experiment_id for e in experiments]

    def _estimate_prior(self, description: str, context: dict[str, Any] | None = None) -> float:
        try:
            prompt = (
                "Estimate the prior probability (0.0-1.0) that the following hypothesis is true before any evidence. Return only a float.\n"
                f"Hypothesis: {description}\nContext: {context or {}}"
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
            logger.error("Prior estimation failed: %s", exc)
            return 0.5

    def _compute_posterior(self, hypothesis: Hypothesis, result: dict[str, Any]) -> float:
        likelihood = float(result.get("likelihood", result.get("confidence", 0.5)))
        prior = hypothesis.prior_probability
        return round(prior * likelihood, 4)
