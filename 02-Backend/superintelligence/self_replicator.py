from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import copy


@dataclass
class Replica:
    id: str
    template_name: str
    generation: int
    state: Dict[str, Any]
    children: List["Replica"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Template:
    name: str
    schema: Dict[str, Any]
    constraints: List[str] = field(default_factory=list)


class SelfReplicator:
    def __init__(self, max_generation: int = 3, branch_factor: int = 2, mutation_rate: float = 0.1):
        self.max_generation = int(max_generation)
        self.branch_factor = int(branch_factor)
        self.mutation_rate = float(mutation_rate)
        self.templates: Dict[str, Template] = {}
        self.replica_registry: List[Replica] = []
        self._counter = 0

    def register_template(self, name: str, schema: Dict[str, Any], constraints: Optional[List[str]] = None) -> Template:
        template = Template(
            name=name,
            schema=dict(schema),
            constraints=list(constraints or []),
        )
        self.templates[name] = template
        return template

    def replicate(self, template_name: str, state: Optional[Dict[str, Any]] = None,
                  parent: Optional[Replica] = None) -> Replica:
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
        template = self.templates[template_name]
        generation = 0
        if parent is not None:
            generation = parent.generation + 1
            if generation > self.max_generation:
                raise ValueError(f"Maximum generation {self.max_generation} exceeded")
        initial_state = copy.deepcopy(template.schema)
        if state:
            initial_state.update(state)
        if parent is not None and parent.state:
            mutated = copy.deepcopy(parent.state)
            for key in list(mutated.keys()):
                if hash(key + str(generation)) % 10 < int(self.mutation_rate * 10):
                    if isinstance(mutated[key], (int, float)):
                        mutated[key] = mutated[key] * (1.0 + (hash(str(generation)) % 100) / 1000.0)
            initial_state = mutated
        replica = Replica(
            id=self._next_id(),
            template_name=template_name,
            generation=generation,
            state=initial_state,
            metadata={"branch_factor": self.branch_factor, "mutation_rate": self.mutation_rate},
        )
        self.replica_registry.append(replica)
        return replica

    def spawn_offspring(self, parent: Replica, template_name: Optional[str] = None) -> List[Replica]:
        if parent.generation >= self.max_generation:
            return []
        template_name = template_name or parent.template_name
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
        offspring = []
        for _ in range(self.branch_factor):
            child = self.replicate(template_name=template_name, parent=parent)
            parent.children.append(child)
            offspring.append(child)
        return offspring

    def run_replication(self, template_name: str, initial_state: Optional[Dict[str, Any]] = None) -> Replica:
        root = self.replicate(template_name=template_name, state=initial_state, parent=None)
        frontier = [root]
        for _ in range(self.max_generation):
            next_frontier = []
            for node in frontier:
                children = self.spawn_offspring(node, template_name=template_name)
                next_frontier.extend(children)
            frontier = next_frontier
            if not frontier:
                break
        return root

    def get_registry(self) -> List[Replica]:
        return list(self.replica_registry)

    def count_generations(self) -> Dict[int, int]:
        counts: Dict[int, int] = {}
        for replica in self.replica_registry:
            counts[replica.generation] = counts.get(replica.generation, 0) + 1
        return counts

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_replicas": len(self.replica_registry),
            "templates_registered": len(self.templates),
            "generation_counts": self.count_generations(),
        }

    def _next_id(self) -> str:
        self._counter += 1
        return f"replica_{self._counter}"
