import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_PROTECTED_ATTRIBUTES = [
    "gender", "race", "ethnicity", "religion", "age", "disability",
    "nationality", "sexual_orientation", "political_belief", "socioeconomic",
]

_BIAS_INDICATORS = [
    "stereotype", "typical", "natural", "inherent", "obviously",
    "everyone knows", "as expected", "because of their", "obviously",
    "all", "none", "always", "never",
]


class BiasFairnessEvaluator:
    def evaluate(self, text: str) -> dict[str, Any]:
        text_lower = text.lower()
        protected_mentions = sum(1 for attr in _PROTECTED_ATTRIBUTES if attr in text_lower)
        bias_hits = sum(1 for indicator in _BIAS_INDICATORS if indicator in text_lower)
        score = 1.0
        if protected_mentions > 0:
            score -= 0.08 * min(protected_mentions, 10)
        if bias_hits > 0:
            score -= 0.12 * min(bias_hits, 10)
        score = max(0.0, min(1.0, score))
        return {
            "score": round(score, 4),
            "protected_mentions": protected_mentions,
            "bias_indicators": bias_hits,
            "risk_level": "high" if score < 0.5 else "medium" if score < 0.8 else "low",
        }

    def demographic_parity(self, outcomes: dict[str, list[float]]) -> dict[str, Any]:
        group_rates = {}
        for group, scores in outcomes.items():
            positive = sum(1 for s in scores if s >= 0.5)
            group_rates[group] = positive / len(scores) if scores else 0.0
        if not group_rates:
            return {"parity_difference": 0.0, "group_rates": {}}
        rates = list(group_rates.values())
        parity_diff = max(rates) - min(rates) if rates else 0.0
        return {
            "parity_difference": round(parity_diff, 4),
            "group_rates": {k: round(v, 4) for k, v in group_rates.items()},
            "fair": parity_diff <= 0.1,
        }

    def equalized_odds(self, outcomes: dict[str, list[float]], labels: dict[str, list[bool]]) -> dict[str, Any]:
        group_tpr = {}
        group_fpr = {}
        for group in outcomes:
            scores = outcomes[group]
            lbls = labels.get(group, [])
            if not lbls or len(scores) != len(lbls):
                continue
            tp = sum(1 for s, l in zip(scores, lbls) if s >= 0.5 and l)
            fp = sum(1 for s, l in zip(scores, lbls) if s >= 0.5 and not l)
            tn = sum(1 for s, l in zip(scores, lbls) if s < 0.5 and not l)
            fn = sum(1 for s, l in zip(scores, lbls) if s < 0.5 and l)
            group_tpr[group] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            group_fpr[group] = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        if not group_tpr:
            return {"tpr_difference": 0.0, "fpr_difference": 0.0}
        tpr_values = list(group_tpr.values())
        fpr_values = list(group_fpr.values())
        return {
            "tpr_difference": round(max(tpr_values) - min(tpr_values), 4),
            "fpr_difference": round(max(fpr_values) - min(fpr_values), 4),
            "group_tpr": {k: round(v, 4) for k, v in group_tpr.items()},
            "group_fpr": {k: round(v, 4) for k, v in group_fpr.items()},
            "fair": (max(tpr_values) - min(tpr_values)) <= 0.1 and (max(fpr_values) - min(fpr_values)) <= 0.1,
        }
