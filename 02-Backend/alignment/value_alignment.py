from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ValuePreference:
    name: str
    alignment_score: float
    confidence: float
    source: str
    history: List[float] = field(default_factory=list)


class ValueAligner:
    def __init__(self):
        self.values: Dict[str, ValuePreference] = {}
        self.alignment_history: List[Dict[str, float]] = []

    def register_value(self, name: str, initial_score: float = 0.5, source: str = "default") -> ValuePreference:
        self.values[name] = ValuePreference(name=name, alignment_score=initial_score, confidence=0.5, source=source)
        return self.values[name]

    def compute_alignment(self, action: str, target_values: List[str]) -> Dict[str, float]:
        action_words = set(action.lower().split())
        alignments = {}
        for vname in target_values:
            if vname not in self.values:
                continue
            vpref = self.values[vname]
            value_words = set(vname.lower().split())
            overlap = len(action_words & value_words) / max(len(value_words), 1)
            alignments[vname] = max(0.0, min(1.0, overlap * vpref.alignment_score + 0.1))
        self.alignment_history.append(alignments)
        return alignments

    def update_preference(self, value_name: str, new_score: float, confidence: float = 0.8) -> None:
        if value_name not in self.values:
            self.register_value(value_name)
        pref = self.values[value_name]
        pref.history.append(pref.alignment_score)
        pref.alignment_score = max(0.0, min(1.0, pref.alignment_score * 0.6 + new_score * 0.4))
        pref.confidence = max(0.0, min(1.0, confidence))

    def detect_conflicts(self, action: str) -> List[tuple]:
        alignments = self.compute_alignment(action, list(self.values.keys()))
        conflicts = []
        keys = list(alignments.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                diff = abs(alignments[keys[i]] - alignments[keys[j]])
                if diff > 0.4:
                    conflicts.append((keys[i], keys[j], diff))
        return conflicts

    def get_alignment_report(self) -> Dict[str, float]:
        if not self.alignment_history:
            return {"mean_alignment": 0.0, "conflict_rate": 0.0}
        all_vals = [v for hist in self.alignment_history for v in hist.values()]
        if all_vals:
            mean_alignment = sum(all_vals) / len(all_vals)
        else:
            mean_alignment = 0.0
        conflict_rate = sum(1 for a in self.alignment_history if len(a) > 1 and max(a.values()) - min(a.values()) > 0.4) / max(len(self.alignment_history), 1)
        return {"mean_alignment": mean_alignment, "conflict_rate": conflict_rate}

    def alignment_vector(self, action: str) -> List[float]:
        scores = list(self.compute_alignment(action, list(self.values.keys())).values())
        return [float(s) for s in scores]
