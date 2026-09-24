from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid
import numpy as np


@dataclass
class Module:
    name: str
    activation: float = 0.0
    content: Optional[np.ndarray] = None
    module_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class GlobalWorkspace:
    def __init__(self, capacity: int = 8, temperature: float = 1.0):
        self.modules: Dict[str, Module] = {}
        self.capacity = capacity
        self.temperature = temperature
        self._broadcast_queue: List[Dict] = []
        self._conscious_contents: List[Module] = []

    def register_module(self, name: str) -> Module:
        if name not in self.modules:
            self.modules[name] = Module(name=name)
        return self.modules[name]

    def activate(self, name: str, activation: float, content: Optional[np.ndarray] = None) -> Module:
        if name not in self.modules:
            self.register_module(name)
        self.modules[name].activation = float(activation)
        if content is not None:
            self.modules[name].content = content
        return self.modules[name]

    def compete(self) -> List[Module]:
        names = list(self.modules.keys())
        if not names:
            return []
        acts = np.array([self.modules[n].activation for n in names])
        exps = np.exp(acts / max(self.temperature, 1e-9))
        if exps.sum() == 0:
            probs = np.ones(len(names)) / len(names)
        else:
            probs = exps / exps.sum()
        sorted_idx = np.argsort(-probs)[: self.capacity]
        winners = [self.modules[names[i]] for i in sorted_idx]
        self._conscious_contents = winners
        return winners

    def broadcast(self) -> List[Dict]:
        if not self._conscious_contents:
            self.compete()
        self._broadcast_queue = [
            {
                "module_id": m.module_id,
                "name": m.name,
                "activation": m.activation,
                "norm": float(np.linalg.norm(m.content)) if m.content is not None else 0.0,
            }
            for m in self._conscious_contents
        ]
        return list(self._broadcast_queue)

    def get_conscious_contents(self) -> List[Module]:
        if not self._conscious_contents:
            self.compete()
        return list(self._conscious_contents)

    def integrate(self, name: str, module: Module) -> None:
        if name not in self.modules:
            self.modules[name] = module
        else:
            target = self.modules[name]
            target.activation = target.activation * 0.5 + module.activation * 0.5
            if target.content is not None and module.content is not None:
                target.content = target.content * 0.5 + module.content * 0.5
