import numpy as np
from typing import List, Dict, Tuple, Optional, Set


class Attribute:
    def __init__(self, name: str, value: float, salience: float = 1.0):
        self.name = name
        self.value = value
        self.salience = salience

    def distance_to(self, other: "Attribute") -> float:
        return abs(self.value - other.value)


class Relation:
    def __init__(self, source: str, target: str, type_: str, weight: float = 1.0):
        self.source = source
        self.target = target
        self.type_ = type_
        self.weight = weight


class Concept:
    def __init__(self, name: str, attributes: Optional[List[Attribute]] = None, relations: Optional[List[Relation]] = None):
        self.name = name
        self.attributes = attributes or []
        self.relations = relations or []

    def add_attribute(self, attr: Attribute):
        self.attributes.append(attr)

    def add_relation(self, rel: Relation):
        self.relations.append(rel)

    def similarity_to(self, other: "Concept", attribute_weight: float = 1.0) -> float:
        if not self.attributes or not other.attributes:
            return 0.0
        self_map = {a.name: a for a in self.attributes}
        other_map = {a.name: a for a in other.attributes}
        common = set(self_map.keys()) & set(other_map.keys())
        if not common:
            return 0.0
        dists = [self_map[k].distance_to(other_map[k]) for k in common]
        return max(0.0, 1.0 - np.mean(dists) * attribute_weight)


class StructureMapping:
    def __init__(self, source: Concept, target: Concept):
        self.source = source
        self.target = target
        self.mapping: Dict[str, str] = {}
        self.candidate_analogies: List[Tuple[str, str, float]] = []

    def compute_mapping(self, relation_weight: float = 0.8, attribute_weight: float = 0.2) -> float:
        rel_score = self._relation_similarity() * relation_weight
        attr_score = self.source.similarity_to(self.target) * attribute_weight
        total = rel_score + attr_score
        return total

    def _relation_similarity(self) -> float:
        if not self.source.relations or not self.target.relations:
            return 0.0
        self_r = {(r.source, r.target, r.type_) for r in self.source.relations}
        other_r = {(r.source, r.target, r.type_) for r in self.target.relations}
        common = self_r & other_r
        return len(common) / max(len(self_r | other_r), 1)

    def find_best_analogy(self, candidates: List[Concept]) -> Tuple[Concept, float]:
        best = None
        best_score = -1.0
        for c in candidates:
            self.source = c
            score = self.compute_mapping()
            if score > best_score:
                best_score = score
                best = c
        return best or candidates[0], best_score


class AnalogyEngine:
    def __init__(self, domain: Optional[List[Concept]] = None, prior_knowledge: Optional[List[Concept]] = None):
        self.domain = domain or []
        self.prior_knowledge = prior_knowledge or []
        self.analogy_cache: List[Tuple[Concept, Concept, float]] = []

    def add_concept(self, concept: Concept, is_prior: bool = False):
        if is_prior:
            self.prior_knowledge.append(concept)
        else:
            self.domain.append(concept)

    def domain_analysis(self) -> Dict[str, float]:
        attr_counts = {}
        for c in self.domain:
            for a in c.attributes:
                attr_counts[a.name] = attr_counts.get(a.name, 0) + 1
        total = len(self.domain) or 1
        return {k: v / total for k, v in attr_counts.items()}

    def search(self, source: Concept) -> List[Tuple[Concept, float]]:
        results = []
        for target in self.domain:
            if target is source:
                continue
            sm = StructureMapping(source, target)
            score = sm.compute_mapping()
            self.analogy_cache.append((source, target, score))
            results.append((target, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def inference(self, source: Concept, target: Concept) -> List[Relation]:
        inferred = []
        source_rel_map = {(r.source, r.target, r.type_): r for r in source.relations}
        target_rel_map = {(r.source, r.target, r.type_): r for r in target.relations}
        for (s, e, t), r in source_rel_map.items():
            for (ts, te, tt), tr in target_rel_map.items():
                if t == tt:
                    inferred.append(Relation(source=ts, target=te, type_=t, weight=r.weight * tr.weight))
        return inferred
