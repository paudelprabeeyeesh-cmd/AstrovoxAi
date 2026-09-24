import numpy as np
from typing import List, Tuple, Optional


class PheromoneGrid:
    def __init__(self, width: int, height: int, evaporation: float = 0.95, seed: Optional[int] = None):
        self.width = width
        self.height = height
        self.evaporation = evaporation
        self.grid = np.zeros((width, height), dtype=float)
        self.rng = np.random.default_rng(seed)

    def deposit(self, x: int, y: int, amount: float) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[x, y] += amount

    def sense(self, x: int, y: int, radius: int = 1) -> float:
        total = 0.0
        count = 0
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    total += self.grid[nx, ny]
                    count += 1
        return total / max(count, 1)

    def evaporate(self) -> None:
        self.grid *= self.evaporation

    def normalize(self) -> None:
        mx = self.grid.max()
        if mx > 0:
            self.grid /= mx


class StigmergicAgent:
    def __init__(self, agent_id: int, grid: PheromoneGrid, start: Tuple[int, int], goal: Tuple[int, int]):
        self.agent_id = agent_id
        self.grid = grid
        self.position = np.array(start, dtype=int)
        self.goal = np.array(goal, dtype=int)
        self.path: List[Tuple[int, int]] = [tuple(self.position.tolist())]
        self.deposit_rate = 1.0

    def step(self) -> bool:
        x, y = int(self.position[0]), int(self.position[1])
        candidates = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.grid.width and 0 <= ny < self.grid.height:
                candidates.append((nx, ny))
        if not candidates:
            return False
        best = max(candidates, key=lambda c: self.grid.sense(c[0], c[1], radius=0))
        self.position = np.array(best, dtype=int)
        self.path.append(tuple(self.position.tolist()))
        dist = np.linalg.norm(self.position - self.goal)
        self.grid.deposit(best[0], best[1], self.deposit_rate / max(len(self.path), 1))
        return dist < 1.5

    def run(self, max_steps: int = 500) -> List[Tuple[int, int]]:
        for _ in range(max_steps):
            if self.step():
                break
        return self.path


class StigmergySimulation:
    def __init__(self, width: int, height: int, n_agents: int, start: Tuple[int, int], goal: Tuple[int, int], seed: Optional[int] = None):
        self.grid = PheromoneGrid(width, height, seed=seed)
        self.agents = [StigmergicAgent(i, self.grid, start, goal) for i in range(n_agents)]

    def run(self, n_iterations: int = 20, max_steps: int = 200) -> List[List[Tuple[int, int]]]:
        paths = []
        for _ in range(n_iterations):
            for agent in self.agents:
                path = agent.run(max_steps=max_steps)
                paths.append(path)
            self.grid.evaporate()
        return paths
