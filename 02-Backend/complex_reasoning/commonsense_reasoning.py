import numpy as np
from typing import List, Dict, Optional


class CommonsenseFact:
    def __init__(self, subject: str, predicate: str, obj: str, confidence: float = 0.9, context: Optional[str] = None):
        self.subject = subject
        self.predicate = predicate
        self.object = obj
        self.confidence = confidence
        self.context = context
        self.exceptions: List[CommonsenseFact] = []

    def add_exception(self, exception: "CommonsenseFact"):
        self.exceptions.append(exception)

    def apply(self, subject: str, obj: str) -> bool:
        if self.subject != subject or self.object != obj:
            return False
        if self.exceptions:
            for exc in self.exceptions:
                if exc.apply(subject, obj):
                    return not exc.override
        return self.confidence > 0.5

    def __repr__(self):
        return f"{self.subject} {self.predicate} {self.object} [{self.confidence}]"


class DefaultRule:
    def __init__(self, if_: str, then_: str, default: bool = True, confidence: float = 0.9):
        self.if_ = if_
        self.then_ = then_
        self.default = default
        self._confidence = confidence

    def can_override(self) -> bool:
        return self.default and self._confidence < 1.0

    def confidence(self) -> float:
        return self._confidence


class CommonsenseKnowledgeBase:
    def __init__(self):
        self.facts: List[CommonsenseFact] = []
        self.defaults: List[DefaultRule] = []
        self.knowledge_graph: Dict[str, List[CommonsenseFact]] = {}
        self.contexts: Dict[str, List[CommonsenseFact]] = {}
        self.confidence_threshold: float = 0.5

    def add_fact(self, fact: CommonsenseFact):
        self.facts.append(fact)
        self.knowledge_graph.setdefault(fact.subject, []).append(fact)
        if fact.context:
            self.contexts.setdefault(fact.context, []).append(fact)

    def add_default(self, rule: DefaultRule):
        self.defaults.append(rule)

    def query(self, subject: str, obj: str, context: Optional[str] = None) -> Optional[CommonsenseFact]:
        candidates = []
        if context and context in self.contexts:
            candidates = [f for f in self.contexts[context] if f.subject == subject and f.object == obj]
        if not candidates:
            candidates = [f for f in self.facts if f.subject == subject and f.object == obj]
        if not candidates:
            return None
        return max(candidates, key=lambda f: f.confidence)

    def inference(self, subject: str, obj: str) -> List[CommonsenseFact]:
        return [f for f in self.facts if f.subject == subject and f.object == obj]

    def model_confidence(self, subject: str) -> float:
        related = self.knowledge_graph.get(subject, [])
        if not related:
            return 0.5
        return float(np.mean([f.confidence for f in related]))

    def non_monotonic(self, fact: CommonsenseFact, new_evidence: CommonsenseFact) -> bool:
        if fact.subject == new_evidence.subject and fact.object == new_evidence.object:
            fact.confidence = min(fact.confidence, new_evidence.confidence)
            return True
        return False


class CommonsenseEngine:
    def __init__(self):
        self.kb = CommonsenseKnowledgeBase()
        self.world_knowledge: Dict[str, Dict[str, float]] = {}

    def add_fact(self, fact: CommonsenseFact):
        self.kb.add_fact(fact)

    def add_default(self, rule: DefaultRule):
        self.kb.add_default(rule)

    def query(self, subject: str, obj: str, context: Optional[str] = None) -> Optional[CommonsenseFact]:
        return self.kb.query(subject, obj, context)

    def inference(self, subject: str, obj: str) -> List[CommonsenseFact]:
        return self.kb.inference(subject, obj)

    def model_confidence(self, subject: str) -> float:
        return self.kb.model_confidence(subject)

    def non_monotonic(self, fact: CommonsenseFact, new_evidence: CommonsenseFact) -> bool:
        return self.kb.non_monotonic(fact, new_evidence)
