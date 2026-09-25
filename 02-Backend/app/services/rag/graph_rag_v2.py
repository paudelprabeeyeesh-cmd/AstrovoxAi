class GraphRAGV2:
    def __init__(self):
        self.graph = {}

    def add_entity(self, entity_id, properties):
        self.graph[entity_id] = properties

    def query(self, entity_id, relation):
        if entity_id not in self.graph:
            return []
        return self.graph[entity_id].get(relation, [])

    def traverse(self, start, depth=3):
        visited = set()
        queue = [(start, 0)]
        while queue:
            current, level = queue.pop(0)
            if current in visited or level > depth:
                continue
            visited.add(current)
            for neighbor in self.graph.get(current, {}).get("relations", []):
                queue.append((neighbor, level + 1))
        return visited
