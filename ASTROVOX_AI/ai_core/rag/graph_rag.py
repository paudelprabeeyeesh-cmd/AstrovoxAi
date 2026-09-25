from typing import Optional, List, Dict, Any, Tuple
import networkx as nx


class GraphRAG:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entities: Dict[str, Dict[str, Any]] = {}

    def add_entity(self, entity_id: str, name: str, entity_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        self.graph.add_node(entity_id, name=name, type=entity_type, properties=properties or {})
        self.entities[entity_id] = {'name': name, 'type': entity_type, 'properties': properties or {}}

    def add_relationship(self, source_id: str, target_id: str, relation: str, properties: Optional[Dict[str, Any]] = None) -> None:
        if source_id in self.graph and target_id in self.graph:
            self.graph.add_edge(source_id, target_id, relation=relation, properties=properties or {})

    def retrieve(self, query: str, top_k: int = 5, traversal_depth: int = 2) -> List[Dict[str, Any]]:
        candidates = []
        for entity_id, data in self.entities.items():
            score = self._compute_relevance(query, data.get('name', ''), data.get('type', ''))
            candidates.append({'id': entity_id, 'name': data['name'], 'type': data['type'], 'score': score})
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:top_k]

    def _compute_relevance(self, query: str, name: str, entity_type: str) -> float:
        query_terms = set(query.lower().split())
        name_terms = set(name.lower().split())
        overlap = len(query_terms & name_terms)
        return overlap / max(len(query_terms), 1)

    def get_subgraph(self, entity_id: str, depth: int = 2) -> nx.DiGraph:
        if entity_id not in self.graph:
            return nx.DiGraph()
        nodes = {entity_id}
        for _ in range(depth):
            new_nodes = set()
            for node in nodes:
                new_nodes.update(self.graph.successors(node))
                new_nodes.update(self.graph.predecessors(node))
            nodes.update(new_nodes)
        return self.graph.subgraph(nodes).copy()

    def community_detection(self) -> Dict[int, List[str]]:
        undirected = self.graph.to_undirected()
        communities = nx.community.greedy_modularity_communities(undirected)
        return {i: list(comm) for i, comm in enumerate(communities)}
