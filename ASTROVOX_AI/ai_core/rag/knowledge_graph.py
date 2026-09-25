from typing import Optional, List, Dict, Any
import networkx as nx
import json


class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.relations: List[Dict[str, str]] = []

    def add_triple(self, subject: str, predicate: str, obj: str, properties: Optional[Dict[str, Any]] = None) -> None:
        if subject not in self.entities:
            self.entities[subject] = {'type': 'entity', 'name': subject}
        if obj not in self.entities:
            self.entities[obj] = {'type': 'entity', 'name': obj}
        self.graph.add_edge(subject, obj, relation=predicate, properties=properties or {})
        self.relations.append({'subject': subject, 'predicate': predicate, 'object': obj, 'properties': properties or {}})

    def query(self, subject: Optional[str] = None, predicate: Optional[str] = None, obj: Optional[str] = None) -> List[Dict[str, str]]:
        results = []
        for rel in self.relations:
            if subject and rel['subject'] != subject:
                continue
            if predicate and rel['predicate'] != predicate:
                continue
            if obj and rel['object'] != obj:
                continue
            results.append(rel)
        return results

    def get_neighbors(self, entity_id: str, direction: str = 'out') -> List[str]:
        if direction == 'out':
            return list(self.graph.successors(entity_id))
        elif direction == 'in':
            return list(self.graph.predecessors(entity_id))
        return list(self.graph.neighbors(entity_id))

    def path_between(self, source: str, target: str) -> Optional[List[str]]:
        try:
            return nx.shortest_path(self.graph, source, target)
        except nx.NetworkXNoPath:
            return None

    def export(self) -> str:
        return json.dumps({'entities': self.entities, 'relations': self.relations}, indent=2)

    @classmethod
    def from_json(cls, data: str) -> 'KnowledgeGraph':
        kg = cls()
        parsed = json.loads(data)
        kg.entities = parsed.get('entities', {})
        kg.relations = parsed.get('relations', [])
        for rel in kg.relations:
            kg.graph.add_edge(rel['subject'], rel['object'], relation=rel['predicate'])
        return kg
