from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np


@dataclass
class TemporalFact:
    id: str
    subject: str
    predicate: str
    object: str
    start_time: datetime
    end_time: Optional[datetime] = None
    confidence: float = 1.0
    source: str = "unknown"


class TemporalKnowledgeBase:
    def __init__(self, default_duration: timedelta = timedelta(days=365)):
        self.facts: Dict[str, TemporalFact] = {}
        self.default_duration = default_duration
        self.index: Dict[str, List[str]] = {}

    def add_fact(self, fact: TemporalFact) -> None:
        self.facts[fact.id] = fact
        for key in [fact.subject, fact.predicate, fact.object]:
            self.index.setdefault(key, []).append(fact.id)

    def query_at(self, subject: str, predicate: str, time: datetime) -> List[TemporalFact]:
        results = []
        candidates = set(self.index.get(subject, [])) & set(self.index.get(predicate, []))
        for fact_id in candidates:
            fact = self.facts[fact_id]
            if fact.start_time <= time:
                if fact.end_time is None or time <= fact.end_time:
                    results.append(fact)
        return results

    def query_interval(self, subject: str, predicate: str, start: datetime, end: datetime) -> List[TemporalFact]:
        results = []
        candidates = set(self.index.get(subject, [])) & set(self.index.get(predicate, []))
        for fact_id in candidates:
            fact = self.facts[fact_id]
            if fact.start_time <= end:
                if fact.end_time is None or start <= fact.end_time:
                    results.append(fact)
        return results

    def temporal_overlap(self, fact1_id: str, fact2_id: str) -> float:
        f1 = self.facts.get(fact1_id)
        f2 = self.facts.get(fact2_id)
        if not f1 or not f2:
            return 0.0
        s1, e1 = f1.start_time, f1.end_time or datetime.max
        s2, e2 = f2.start_time, f2.end_time or datetime.max
        overlap_start = max(s1, s2)
        overlap_end = min(e1, e2)
        if overlap_start >= overlap_end:
            return 0.0
        overlap = (overlap_end - overlap_start).total_seconds()
        min_dur = min((e1 - s1).total_seconds(), (e2 - s2).total_seconds())
        return overlap / min_dur if min_dur > 0 else 0.0

    def temporal_distance(self, fact1_id: str, fact2_id: str) -> Optional[float]:
        f1 = self.facts.get(fact1_id)
        f2 = self.facts.get(fact2_id)
        if not f1 or not f2:
            return None
        e1 = f1.end_time or datetime.max
        s2 = f2.start_time
        if e1 <= s2:
            return (s2 - e1).total_seconds()
        e2 = f2.end_time or datetime.max
        s1 = f1.start_time
        if e2 <= s1:
            return (s1 - e2).total_seconds()
        return 0.0

    def infer_transitivity(self) -> List[TemporalFact]:
        inferred = []
        fact_list = list(self.facts.values())
        for i, f1 in enumerate(fact_list):
            for f2 in fact_list[i + 1 :]:
                if f1.object == f2.subject and f1.predicate == f2.predicate:
                    if f1.end_time is None or f2.start_time >= f1.end_time:
                        new_id = f"{f1.id}_trans_{f2.id}"
                        inferred.append(
                            TemporalFact(
                                id=new_id,
                                subject=f1.subject,
                                predicate=f1.predicate,
                                object=f2.object,
                                start_time=f1.start_time,
                                end_time=f2.end_time,
                                confidence=min(f1.confidence, f2.confidence) * 0.8,
                                source="transitivity",
                            )
                        )
        return inferred

    def decay_confidence(self, reference_time: datetime, half_life: timedelta) -> None:
        for fact in self.facts.values():
            age = (reference_time - fact.start_time).total_seconds()
            half_life_sec = half_life.total_seconds()
            decay = np.exp(-age * np.log(2) / half_life_sec)
            fact.confidence = max(0.0, min(1.0, fact.confidence * decay))
