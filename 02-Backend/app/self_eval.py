import logging
from dataclasses import dataclass, field
from typing import Any

from ...config import settings

logger = logging.getLogger(__name__)


@dataclass
class Evaluation:
    prompt: str
    response: str
    score: float = 0.0
    confidence: float = 0.0
    issues: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SelfEvaluator:
    def __init__(self, llm_client: Any | None = None):
        self.llm = llm_client
        self._openai = None

    def _get_openai(self):
        if self._openai is None:
            import openai
            self._openai = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def evaluate_response(self, prompt: str, response: str, context: dict[str, Any] | None = None) -> Evaluation:
        eval_prompt = (
            "Evaluate the assistant response for relevance, accuracy, and completeness on a 0-1 scale. "
            "Return JSON with keys: score (float), issues (list of strings), improvements (list of strings).\n"
            f"Prompt: {prompt}\nResponse: {response}\nContext: {context or {}}"
        )
        try:
            client = self._get_openai()
            res = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": eval_prompt}],
                temperature=0.0,
            )
            import json
            content = res.choices[0].message.content or "{}"
            data = json.loads(content)
            evaluation = Evaluation(
                prompt=prompt,
                response=response,
                score=float(data.get("score", 0.0)),
                issues=list(data.get("issues", [])),
                improvements=list(data.get("improvements", [])),
                metadata={"context": context or {}},
            )
            evaluation.confidence = self.calculate_confidence(response, context or {})
            return evaluation
        except Exception as e:
            logger.error(f"Self-evaluation failed: {e}")
            return Evaluation(prompt=prompt, response=response, score=0.0, issues=[str(e)], improvements=[])

    def calculate_confidence(self, response: str, context: dict[str, Any]) -> float:
        length_score = min(len(response) / 500.0, 1.0)
        context_score = 0.5 if context else 0.3
        return round((length_score + context_score) / 2.0, 2)

    def generate_improvements(self, response: str, evaluation: Evaluation) -> list[str]:
        if not evaluation.improvements:
            return ["Add supporting evidence", "Clarify ambiguous statements"]
        return evaluation.improvements

    def log_evaluation(self, prompt: str, response: str, evaluation: Evaluation) -> None:
        logger.info(
            "Evaluation logged",
            extra={
                "prompt": prompt[:200],
                "response": response[:200],
                "score": evaluation.score,
                "confidence": evaluation.confidence,
                "issues": evaluation.issues,
                "improvements": evaluation.improvements,
            },
        )
