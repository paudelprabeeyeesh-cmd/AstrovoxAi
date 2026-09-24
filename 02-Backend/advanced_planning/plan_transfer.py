import math
import random
import statistics
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


def _vec_len(v):
    return math.sqrt(sum(x * x for x in v))


def _vec_sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _vec_clamp(v, lo, hi):
    return [max(lo_val, min(hi_val, x)) for lo_val, hi_val, x in zip(lo, hi, v)]


def _vec_sum(v):
    return sum(v)


def _softmax(logits):
    m = max(logits)
    e = [math.exp(x - m) for x in logits]
    s = sum(e)
    return [x / s for x in e]


class DomainMapping:
    def __init__(self, source_domain: str, target_domain: str):
        self.source_domain = source_domain
        self.target_domain = target_domain
        self.action_mapping: Dict[str, str] = {}
        self.state_mapping: Dict[str, str] = {}
        self.predicate_mapping: Dict[str, str] = {}
        self.transfer_score: Dict[str, float] = {}

    def map_action(self, source_action: str, target_action: str, confidence: float = 1.0) -> None:
        self.action_mapping[source_action] = target_action
        self.transfer_score[source_action] = confidence

    def map_predicate(self, source_pred: str, target_pred: str) -> None:
        self.predicate_mapping[source_pred] = target_pred

    def translate_plan(self, source_plan: List[Any]) -> List[Any]:
        return [self.action_mapping.get(str(a), str(a)) for a in source_plan]

    def similarity(self, source_state: Any, target_state: Any) -> float:
        if isinstance(source_state, dict) and isinstance(target_state, dict):
            common_keys = set(source_state.keys()) & set(target_state.keys())
            if not common_keys:
                return 0.0
            matches = sum(1 for k in common_keys if source_state[k] == target_state[k])
            return matches / len(common_keys)
        return 0.0


class PlanTransfer:
    def __init__(self):
        self.domain_mappings: List[DomainMapping] = []
        self.transfer_history: List[Dict[str, Any]] = []

    def register_mapping(self, mapping: DomainMapping) -> None:
        self.domain_mappings.append(mapping)

    def transfer(self, source_plan: List[Any], source_domain: str, target_domain: str,
                 adapt_fn: Optional[Callable[[Any], Any]] = None) -> Tuple[List[Any], float]:
        mapping = next((m for m in self.domain_mappings if m.source_domain == source_domain
                        and m.target_domain == target_domain), None)
        if mapping is None:
            return source_plan, 0.0
        translated = mapping.translate_plan(source_plan)
        if adapt_fn:
            translated = [adapt_fn(a) for a in translated]
        scores = [mapping.transfer_score.get(str(a), 0.0) for a in source_plan]
        confidence = statistics.mean(scores) if scores else 0.0
        self.transfer_history.append({"source_plan": source_plan, "translated_plan": translated,
                                      "confidence": confidence})
        return translated, confidence

    def adapt_plan(self, plan: List[Any], target_context: Dict[str, Any],
                   adaptation_fn: Callable[[Any, Dict], Any]) -> List[Any]:
        return [adaptation_fn(a, target_context) for a in plan]

    def evaluate_transfer_quality(self, source_plan: List[Any], target_plan: List[Any],
                                  mapping: DomainMapping) -> float:
        if not source_plan or not target_plan:
            return 0.0
        scores = []
        for s, t in zip(source_plan, target_plan):
            score = mapping.transfer_score.get(str(s), 0.0)
            matched = str(t) == mapping.action_mapping.get(str(s), "")
            scores.append(score if matched else 0.0)
        return statistics.mean(scores) if scores else 0.0
