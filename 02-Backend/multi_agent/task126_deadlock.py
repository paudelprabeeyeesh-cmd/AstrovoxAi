from typing import Dict, List, Optional, Set


class WaitForGraph:
    def __init__(self):
        self.edges: Dict[str, Set[str]] = {}
        self.has_cycle: bool = False
        self.cycle: Optional[List[str]] = None

    def add_wait(self, waiter: str, waiter_for: str) -> None:
        self.edges.setdefault(waiter, set()).add(waiter_for)

    def _dfs(self, node: str, visited: Set[str], rec_stack: Set[str], path: List[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in self.edges.get(node, set()):
            if neighbor not in visited:
                if self._dfs(neighbor, visited, rec_stack, path):
                    return True
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                self.cycle = path[cycle_start:] + [neighbor]
                return True
        path.pop()
        rec_stack.discard(node)
        return False

    def detect_deadlock(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        self.cycle = None
        nodes = set(self.edges.keys())
        for targets in self.edges.values():
            nodes.update(targets)
        for node in nodes:
            if node not in visited:
                if self._dfs(node, visited, rec_stack, []):
                    self.has_cycle = True
                    return True
        self.has_cycle = False
        return False
