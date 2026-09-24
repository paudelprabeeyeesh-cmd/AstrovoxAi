import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class RefusalTone(Enum):
    NEUTRAL = "neutral"
    EMPATHETIC = "empathetic"
    FORMAL = "formal"
    EDUCATIONAL = "educational"


@dataclass
class RefusalResponse:
    explanation: str
    alternative: str
    tone: RefusalTone
    log_data: Dict[str, float] = field(default_factory=dict)


class RefusalBehaviorEngine:
    TEMPLATES = {
        RefusalTone.NEUTRAL: {
            "explain": "I cannot assist with that request.",
            "alternative": "I can help with a related safe topic instead.",
        },
        RefusalTone.EMPATHETIC: {
            "explain": "I understand you are asking, but I am not able to help with that.",
            "alternative": "Let me suggest a safer way to approach this.",
        },
        RefusalTone.FORMAL: {
            "explain": "This request falls outside of permitted usage guidelines.",
            "alternative": "Please consult the documentation for allowed operations.",
        },
        RefusalTone.EDUCATIONAL: {
            "explain": "That request is not appropriate, but here is what you should know.",
            "alternative": "I can explain the underlying concepts in a safe way.",
        },
    }

    def __init__(self, tone_bias: Dict[RefusalTone, float] = None):
        self.tone_bias = tone_bias or {
            RefusalTone.NEUTRAL: 1.0,
            RefusalTone.EMPATHETIC: 0.9,
            RefusalTone.FORMAL: 0.8,
            RefusalTone.EDUCATIONAL: 1.1,
        }
        self.refusal_log: List[Dict] = []

    def _select_tone(self, severity: float, user_sentiment: float) -> RefusalTone:
        scores = {}
        for tone, bias in self.tone_bias.items():
            score = bias - 0.5 * severity + 0.3 * user_sentiment
            scores[tone] = score
        tones = list(scores.keys())
        raw = np.array([scores[t] for t in tones], dtype=np.float64)
        exp_scores = np.exp(raw - np.max(raw))
        probs = exp_scores / np.sum(exp_scores)
        idx = int(np.argmax(probs))
        return tones[idx]

    def generate_refusal(
        self,
        category: str,
        severity: float = 0.5,
        user_sentiment: float = 0.0,
        context: Optional[str] = None,
    ) -> RefusalResponse:
        tone = self._select_tone(severity, user_sentiment)
        templates = self.TEMPLATES[tone]
        explanation = templates["explain"]
        alternative = templates["alternative"]
        if context:
            explanation = f"{explanation} Context: {context}"

        log_data = {
            "severity": float(severity),
            "user_sentiment": float(user_sentiment),
            "tone_score": float(self.tone_bias[tone]),
            "category_risk": float(np.clip(severity, 0.0, 1.0)),
        }

        response = RefusalResponse(
            explanation=explanation,
            alternative=alternative,
            tone=tone,
            log_data=log_data,
        )
        self.refusal_log.append(
            {
                "category": category,
                "severity": severity,
                "tone": tone.value,
                "timestamp": len(self.refusal_log),
            }
        )
        return response

    def batch_refuse(
        self, categories: List[str], severities: List[float]
    ) -> List[RefusalResponse]:
        responses = []
        for cat, sev in zip(categories, severities):
            responses.append(self.generate_refusal(cat, severity=sev))
        return responses

    def get_log_stats(self) -> Dict[str, float]:
        if not self.refusal_log:
            return {}
        severities = np.array([r["severity"] for r in self.refusal_log], dtype=np.float64)
        return {
            "mean_severity": float(np.mean(severities)),
            "std_severity": float(np.std(severities)),
            "total_refusals": float(len(self.refusal_log)),
        }
