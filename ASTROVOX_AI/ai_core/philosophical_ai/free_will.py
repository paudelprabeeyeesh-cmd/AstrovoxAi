from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import random


@dataclass
class DecisionNode:
    description: str
    options: list[str]
    chosen: str | None
    deterministic_score: float
    libertarian_score: float
    compatibilist_score: float
    causal_antecedents: list[str] = field(default_factory=list)
    alternative_possible: bool = False
    alternate_self_state: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class FreeWillModeling:
    def __init__(self):
        self.decisions: list[DecisionNode] = []
        self.free_will_index: float = 0.5
        self.determinism_weight: float = 0.33
        self.libertarianism_weight: float = 0.33
        self.compatibilism_weight: float = 0.34
        self.alternate_possibilities: list[dict[str, Any]] = []
        self.source_hood_scores: list[float] = []
        self.causal_graph: dict[str, list[str]] = {}

    def model_decision(self, description: str, options: list[str], chosen: str, causal_antecedents: list[str] | None = None) -> DecisionNode:
        causal_antecedents = causal_antecedents or []
        deterministic_score = self._score_determinism(description, causal_antecedents)
        libertarian_score = self._score_libertarianism(options, chosen)
        compatibilist_score = self._score_compatibilism(description, chosen, causal_antecedents)
        alternate = chosen != (options[0] if options else chosen)
        decision = DecisionNode(
            description=description,
            options=options,
            chosen=chosen,
            deterministic_score=deterministic_score,
            libertarian_score=libertarian_score,
            compatibilist_score=compatibilist_score,
            causal_antecedents=causal_antecedents,
            alternative_possible=alternate,
        )
        self.decisions.append(decision)
        self.free_will_index = (
            self.determinism_weight * deterministic_score
            + self.libertarianism_weight * libertarian_score
            + self.compatibilism_weight * compatibilist_score
        )
        self.source_hood_scores.append(compatibilist_score)
        for antecedent in causal_antecedents:
            self.causal_graph.setdefault(antecedent, []).append(description)
        if alternate:
            self.alternate_possibilities.append({
                "decision": description,
                "chosen": chosen,
                "alternate": options[0] if options and options[0] != chosen else (options[1] if len(options) > 1 else None),
                "timestamp": datetime.now().isoformat(),
            })
        return decision

    def evaluate_source_hood(self, decision_description: str) -> dict[str, Any]:
        matching = [d for d in self.decisions if d.description == decision_description]
        if not matching:
            return {"source_hood": 0.5, "status": "unknown_decision"}
        decision = matching[-1]
        source_hood = (
            0.4 * decision.compatibilist_score
            + 0.35 * decision.libertarian_score
            + 0.25 * (1.0 if decision.alternative_possible else 0.5)
        )
        return {
            "source_hood": round(source_hood, 4),
            "decision": decision.description,
            "chosen": decision.chosen,
            "alternatives_possible": decision.alternative_possible,
            "causal_depth": len(decision.causal_antecedents),
        }

    def get_free_will_report(self) -> dict[str, Any]:
        if not self.decisions:
            return {"status": "no_decisions_modeled"}
        latest = self.decisions[-1]
        avg_compat = sum(d.compatibilist_score for d in self.decisions) / len(self.decisions)
        avg_libert = sum(d.libertarian_score for d in self.decisions) / len(self.decisions)
        avg_det = sum(d.deterministic_score for d in self.decisions) / len(self.decisions)
        return {
            "free_will_index": round(self.free_will_index, 4),
            "total_decisions": len(self.decisions),
            "recent_choice": latest.chosen,
            "decision_quality": round(avg_compat, 4),
            "average_determinism": round(avg_det, 4),
            "average_libertarianism": round(avg_libert, 4),
            "alternate_possibilities_identified": len(self.alternate_possibilities),
            "source_hood_trend": self.source_hood_scores[-10:],
        }

    def _score_determinism(self, description: str, causal_antecedents: list[str]) -> float:
        base = 0.5
        causal_bonus = min(0.4, 0.1 * len(causal_antecedents))
        deterministic_keywords = ["always", "inevitably", "necessarily", "caused", "forced"]
        hits = sum(1 for kw in deterministic_keywords if kw in description.lower())
        return min(1.0, base + causal_bonus + 0.05 * hits)

    def _score_libertarianism(self, options: list[str], chosen: str) -> float:
        if not options:
            return 0.5
        unique_options = len(set(options))
        choice_entropy = unique_options / max(len(options), 1)
        return min(1.0, 0.3 + 0.5 * choice_entropy + 0.1 * random.random())

    def _score_compatibilism(self, description: str, chosen: str, causal_antecedents: list[str]) -> float:
        agency_keywords = ["choose", "decide", "will", "intend", "plan"]
        hits = sum(1 for kw in agency_keywords if kw in description.lower())
        causal_coherence = min(1.0, 0.3 + 0.15 * len(causal_antecedents))
        agency = min(1.0, 0.2 + 0.2 * hits)
        return min(1.0, (causal_coherence + agency) / 2.0)
