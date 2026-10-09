from typing import Any, Dict, List, Optional, Tuple


class AnalogicalReasoner:
    def __init__(self):
        self._source_domain: List[Dict[str, Any]] = []
        self._target_domain: List[Dict[str, Any]] = []
        self._mappings: List[Dict[str, Any]] = []

    def add_source_fact(self, relation: str, subject: str, obj: str) -> None:
        self._source_domain.append({"relation": relation, "subject": subject, "object": obj})

    def add_target_fact(self, relation: str, subject: str, obj: str) -> None:
        self._target_domain.append({"relation": relation, "subject": subject, "object": obj})

    def map_relations(self) -> List[Dict[str, Any]]:
        mappings = []
        source_relations = {f["relation"] for f in self._source_domain}
        target_relations = {f["relation"] for f in self._target_domain}
        common = source_relations & target_relations
        for relation in common:
            mappings.append({"relation": relation, "confidence": 1.0})
        self._mappings.extend(mappings)
        return mappings

    def infer_target(self, source_fact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for mapping in self._mappings:
            if source_fact["relation"] == mapping["relation"]:
                return {
                    "relation": source_fact["relation"],
                    "subject": source_fact["subject"],
                    "object": source_fact["object"],
                    "confidence": mapping["confidence"],
                }
        return None
